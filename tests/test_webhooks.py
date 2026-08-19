"""The webhook view: verification and parsing are delegated to the SDK, dispatch is Django's.

Deliveries are signed with the SDK's own ``sign``, the mirror of the verifier the view
calls. Recomputing the HMAC here from the signature scheme would agree with this file's
author rather than with the SDK, and the two would drift silently.
"""

from __future__ import annotations

import json
from datetime import UTC, datetime

import pytest
from django.test import Client, override_settings
from mailkube import EmailSentEvent, UnknownEvent, sign

from mailkube_django.webhooks import webhook_received

SECRET = "whsec_test"
EVENT = {
    "type": "email.sent",
    "created_at": "2026-08-19T10:00:00Z",
    "data": {
        "email_id": "abc123",
        "created_at": "2026-08-19T10:00:00Z",
        "domain": "example.com",
        "subject": "Welcome",
        "to": ["rcpt@example.com"],
        "from": "sender@example.com",
        "sent": {"recipient": "rcpt@example.com", "timestamp": "2026-08-19T10:00:01Z"},
    },
}


def signed(body: bytes) -> dict[str, str]:
    stamp = datetime.now(UTC).isoformat()
    return {
        "HTTP_X_WEBHOOK_ID": "wh_1",
        "HTTP_X_WEBHOOK_TS": stamp,
        "HTTP_X_WEBHOOK_SIG": sign("wh_1", stamp, body, SECRET),
    }


def post(payload: dict, headers: dict[str, str] | None = None):
    body = json.dumps(payload).encode()
    return Client().post("/webhooks/", data=body, content_type="application/json", **(headers or signed(body)))


@pytest.fixture
def received():
    events = []

    # weak=False: a local function has no other strong reference, and Django's default
    # weak connection would collect it before the view ever fires the signal.
    def collect(sender, event, **kwargs):
        events.append(event)

    webhook_received.connect(collect, weak=False)
    yield events
    webhook_received.disconnect(collect)


def test_a_verified_webhook_dispatches_a_typed_event(received):
    response = post(EVENT)

    assert response.status_code == 200
    (event,) = received
    assert isinstance(event, EmailSentEvent)
    assert event.data.email_id == "abc123"
    assert event.data.sent.recipient == "rcpt@example.com"


def test_an_unrecognized_event_type_still_reaches_the_receiver(received):
    # A platform event this SDK version predates must not 400: receivers keep working and
    # upgrade on their own schedule. The SDK routes it to UnknownEvent rather than raising.
    response = post({"type": "email.teleported", "created_at": "2026-08-19T10:00:00Z", "data": {"whatever": 1}})

    assert response.status_code == 200
    (event,) = received
    assert isinstance(event, UnknownEvent)
    assert event.type == "email.teleported"
    assert event.data == {"whatever": 1}


def test_a_signed_but_unreadable_payload_is_rejected(received):
    # Correct signature, but the body is not an event: the envelope claims email.sent and
    # carries none of its fields. 400, not a 500 from an escaping ValidationError.
    response = post({"type": "email.sent", "created_at": "2026-08-19T10:00:00Z", "data": {}})

    assert response.status_code == 400
    assert response.json()["detail"] == "Malformed webhook payload."
    assert received == []


def test_a_tampered_body_is_rejected(received):
    headers = signed(json.dumps(EVENT).encode())
    response = Client().post("/webhooks/", data=b'{"type":"email.bounced"}', content_type="application/json", **headers)

    assert response.status_code == 400
    assert received == []


def test_missing_signature_headers_are_rejected(received):
    body = json.dumps(EVENT).encode()
    response = Client().post("/webhooks/", data=body, content_type="application/json")

    assert response.status_code == 400
    assert received == []


@override_settings(MAILKUBE_WEBHOOK_SECRET=None)
def test_an_unconfigured_secret_fails_loudly_rather_than_accepting_anything(received):
    response = post(EVENT)

    assert response.status_code == 500
    assert received == []
