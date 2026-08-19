"""The standalone backend: message mapping, lifecycle, and fail_silently.

These drive ``EmailBackend`` directly rather than ``django.core.mail.send_mail``, because
pytest-django swaps ``EMAIL_BACKEND`` for the locmem backend during tests, so a plain
``send_mail`` would never reach this package at all.
"""

from __future__ import annotations

import pytest
from django.core.mail import EmailMessage, EmailMultiAlternatives
from mailkube import InvalidRequestError

from conftest import capturing_handler, error_handler, ok_handler, patch_sdk
from mailkube_django.backends import EmailBackend


def send(message, **kwargs) -> int:
    return EmailBackend(**kwargs).send_messages([message])


def plain(**kwargs) -> EmailMessage:
    return EmailMessage("Hi", "plain body", "from@x.com", ["to@y.com"], **kwargs)


def test_a_message_is_posted_to_the_emails_endpoint(monkeypatch):
    captured: dict = {}
    patch_sdk(monkeypatch, capturing_handler(captured))

    assert send(plain()) == 1
    assert captured["url"].endswith("/emails")
    assert captured["body"]["from"] == "from@x.com"
    assert captured["body"]["to"] == ["to@y.com"]
    assert captured["body"]["subject"] == "Hi"
    assert captured["body"]["text"] == "plain body"


def test_html_alternatives_become_the_html_field(monkeypatch):
    captured: dict = {}
    patch_sdk(monkeypatch, capturing_handler(captured))

    message = EmailMultiAlternatives("Hi", "plain", "from@x.com", ["to@y.com"])
    message.attach_alternative("<p>rich</p>", "text/html")
    send(message)

    assert captured["body"]["text"] == "plain"
    assert captured["body"]["html"] == "<p>rich</p>"


def test_an_html_content_subtype_message_sends_only_html(monkeypatch):
    captured: dict = {}
    patch_sdk(monkeypatch, capturing_handler(captured))

    message = EmailMessage("Hi", "<p>rich</p>", "from@x.com", ["to@y.com"])
    message.content_subtype = "html"
    send(message)

    assert captured["body"]["html"] == "<p>rich</p>"
    assert "text" not in captured["body"]


def test_cc_bcc_reply_to_and_headers_are_forwarded(monkeypatch):
    captured: dict = {}
    patch_sdk(monkeypatch, capturing_handler(captured))

    send(
        plain(
            cc=["cc@y.com"],
            bcc=["bcc@y.com"],
            reply_to=["reply@y.com"],
            headers={"In-Reply-To": "<prev@x>"},
        )
    )

    assert captured["body"]["cc"] == ["cc@y.com"]
    assert captured["body"]["bcc"] == ["bcc@y.com"]
    assert captured["body"]["reply_to"] == ["reply@y.com"]
    assert captured["body"]["headers"] == {"In-Reply-To": "<prev@x>"}


def test_attachment_content_is_base64_encoded(monkeypatch):
    """Django decodes text/* attachments to str, which is raw content, not base64."""
    captured: dict = {}
    patch_sdk(monkeypatch, capturing_handler(captured))

    message = plain()
    message.attach("a.txt", b"hello", "text/plain")
    send(message)

    attached = captured["body"]["attachments"][0]
    assert attached["filename"] == "a.txt"
    assert attached["content"] == "aGVsbG8="
    assert attached["content_type"] == "text/plain"


def test_binary_attachment_content_is_base64_encoded(monkeypatch):
    captured: dict = {}
    patch_sdk(monkeypatch, capturing_handler(captured))

    message = plain()
    message.attach("a.bin", b"\x00\x01\x02", "application/octet-stream")
    send(message)

    assert captured["body"]["attachments"][0]["content"] == "AAEC"


def test_the_api_key_from_settings_reaches_the_sdk(monkeypatch):
    seen = patch_sdk(monkeypatch, ok_handler)
    send(plain())
    assert seen["kwargs"]["api_key"] == "mk_test"


def test_a_constructor_override_beats_the_setting(monkeypatch):
    seen = patch_sdk(monkeypatch, ok_handler)
    send(plain(), api_key="mk_override")
    assert seen["kwargs"]["api_key"] == "mk_override"


def test_an_api_error_propagates_by_default(monkeypatch):
    patch_sdk(monkeypatch, error_handler(422))
    with pytest.raises(InvalidRequestError):
        send(plain())


def test_fail_silently_swallows_the_error_and_reports_zero_sent(monkeypatch):
    patch_sdk(monkeypatch, error_handler(422))
    assert send(plain(), fail_silently=True) == 0


def test_a_message_with_no_recipients_is_skipped(monkeypatch):
    patch_sdk(monkeypatch, ok_handler)
    assert send(EmailMessage("Hi", "body", "from@x.com", [])) == 0


def test_an_empty_batch_short_circuits(monkeypatch):
    patch_sdk(monkeypatch, ok_handler)
    assert EmailBackend().send_messages([]) == 0


def test_a_batch_reports_how_many_were_accepted(monkeypatch):
    patch_sdk(monkeypatch, ok_handler)
    assert EmailBackend().send_messages([plain(), plain(), plain()]) == 3


def test_open_is_idempotent_and_close_releases_the_client(monkeypatch):
    patch_sdk(monkeypatch, ok_handler)
    backend = EmailBackend()

    assert backend.open() is True
    assert backend.open() is False
    backend.close()
    assert backend.client is None
    backend.close()  # closing twice is safe


def test_a_missing_api_key_raises_unless_fail_silently(settings):
    settings.MAILKUBE_API_KEY = None
    with pytest.raises(Exception, match="No API key provided"):
        EmailBackend(api_key=None).open()


def test_a_missing_api_key_is_swallowed_when_fail_silently(settings, monkeypatch):
    monkeypatch.delenv("MAILKUBE_API_KEY", raising=False)
    settings.MAILKUBE_API_KEY = None
    backend = EmailBackend(fail_silently=True)

    assert backend.open() is False
    assert backend.send_messages([plain()]) == 0


def test_the_standalone_backend_never_imports_anymail():
    """The zero-extra-dependency promise, asserted rather than trusted."""
    import subprocess  # noqa: PLC0415
    import sys  # noqa: PLC0415

    code = "import sys; import mailkube_django.backends; sys.exit(1 if 'anymail' in sys.modules else 0)"
    assert subprocess.run([sys.executable, "-c", code], check=False).returncode == 0
