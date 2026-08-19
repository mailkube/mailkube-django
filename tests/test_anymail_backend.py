"""The Anymail backend.

Skipped entirely when the ``[anymail]`` extra is not installed, so one test tree serves
both install shapes. CI runs the suite twice, once without the extra and once with it, so
these do not silently never execute.
"""

from __future__ import annotations

import pytest

pytest.importorskip("anymail")

from datetime import UTC, datetime

from django.core.mail import EmailMultiAlternatives
from django.test import override_settings

from conftest import capturing_handler, error_handler, ok_handler, patch_sdk
from mailkube_django.anymail_backend import EmailBackend

BACKEND = "mailkube_django.anymail_backend.EmailBackend"


def send(message):
    """Send through this package's backend explicitly.

    pytest-django swaps ``EMAIL_BACKEND`` for locmem during tests, so the tests that go
    through Django's plumbing also carry ``@override_settings``.
    """
    message.send()


@override_settings(EMAIL_BACKEND=BACKEND)
def test_send_posts_the_message_through_the_sdk(monkeypatch):
    captured: dict = {}
    patch_sdk(monkeypatch, capturing_handler(captured))

    message = EmailMultiAlternatives("Hi", "plain", "Acme <from@x.com>", ["to@y.com"])
    message.attach_alternative("<p>rich</p>", "text/html")
    send(message)

    assert captured["url"].endswith("/emails")
    assert captured["body"]["from"] == "Acme <from@x.com>"
    assert captured["body"]["to"] == ["to@y.com"]
    assert captured["body"]["text"] == "plain"
    assert captured["body"]["html"] == "<p>rich</p>"


@override_settings(EMAIL_BACKEND=BACKEND)
def test_recipient_status_reports_the_accepted_message_id(monkeypatch):
    patch_sdk(monkeypatch, ok_handler)

    message = EmailMultiAlternatives("Hi", "body", "from@x.com", ["to@y.com"])
    send(message)

    status = message.anymail_status
    assert status.recipients["to@y.com"].status == "queued"
    assert status.recipients["to@y.com"].message_id == "abc123"


@override_settings(EMAIL_BACKEND=BACKEND)
def test_anymail_tags_map_onto_the_api_name_value_tags(monkeypatch):
    captured: dict = {}
    patch_sdk(monkeypatch, capturing_handler(captured))

    message = EmailMultiAlternatives("Hi", "body", "from@x.com", ["to@y.com"])
    message.tags = ["welcome", "onboarding"]
    send(message)

    assert captured["body"]["tags"] == [
        {"name": "welcome", "value": ""},
        {"name": "onboarding", "value": ""},
    ]


@override_settings(EMAIL_BACKEND=BACKEND)
def test_send_at_schedules_the_message(monkeypatch):
    captured: dict = {}
    scheduled = {"id": "abc123", "scheduled_at": "2099-01-01T00:00:00Z"}
    patch_sdk(monkeypatch, capturing_handler(captured, payload=scheduled))

    message = EmailMultiAlternatives("Hi", "body", "from@x.com", ["to@y.com"])
    message.send_at = datetime(2099, 1, 1, tzinfo=UTC)
    send(message)

    assert captured["body"]["scheduled_at"] == "2099-01-01T00:00:00+00:00"
    # Anymail's status vocabulary is a closed set with no "scheduled" member.
    assert message.anymail_status.recipients["to@y.com"].status == "queued"


@override_settings(EMAIL_BACKEND=BACKEND)
def test_template_and_merge_global_data_map_to_template_fields(monkeypatch):
    captured: dict = {}
    patch_sdk(monkeypatch, capturing_handler(captured))

    message = EmailMultiAlternatives("Hi", "body", "from@x.com", ["to@y.com"])
    message.template_id = "tpl_1"
    message.merge_global_data = {"name": "Ada"}
    send(message)

    assert captured["body"]["template_id"] == "tpl_1"
    assert captured["body"]["variables"] == {"name": "Ada"}


@override_settings(EMAIL_BACKEND=BACKEND)
def test_esp_extra_passes_through_untouched(monkeypatch):
    captured: dict = {}
    patch_sdk(monkeypatch, capturing_handler(captured))

    message = EmailMultiAlternatives("Hi", "body", "from@x.com", ["to@y.com"])
    message.esp_extra = {"topic": "newsletter"}
    send(message)

    assert captured["body"]["topic"] == "newsletter"


@override_settings(EMAIL_BACKEND=BACKEND)
def test_attachments_reuse_the_shared_conversion(monkeypatch):
    captured: dict = {}
    patch_sdk(monkeypatch, capturing_handler(captured))

    message = EmailMultiAlternatives("Hi", "body", "from@x.com", ["to@y.com"])
    message.attach("a.txt", b"hello", "text/plain")
    send(message)

    attached = captured["body"]["attachments"][0]
    assert attached["filename"] == "a.txt"
    assert attached["content"] == "aGVsbG8="  # base64, via the shared _payload.attachment


@override_settings(EMAIL_BACKEND=BACKEND)
def test_an_sdk_error_is_translated_into_an_anymail_error(monkeypatch):
    from anymail.exceptions import AnymailAPIError  # noqa: PLC0415

    patch_sdk(monkeypatch, error_handler(422))
    message = EmailMultiAlternatives("Hi", "body", "from@x.com", ["to@y.com"])

    with pytest.raises(AnymailAPIError):
        send(message)


@override_settings(EMAIL_BACKEND=BACKEND)
def test_fail_silently_relies_on_that_translation(monkeypatch):
    """Anymail only suppresses its own error types, which is why post_to_esp translates."""
    patch_sdk(monkeypatch, error_handler(422))
    message = EmailMultiAlternatives("Hi", "body", "from@x.com", ["to@y.com"])
    assert message.send(fail_silently=True) == 0


def test_cc_and_bcc_are_recorded_for_status(monkeypatch):
    patch_sdk(monkeypatch, ok_handler)
    backend = EmailBackend()
    message = EmailMultiAlternatives("Hi", "body", "from@x.com", ["to@y.com"], cc=["cc@y.com"])

    assert backend.send_messages([message]) == 1
    assert set(message.anymail_status.recipients) == {"to@y.com", "cc@y.com"}
