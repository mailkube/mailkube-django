"""The Django-message to SDK-kwargs translation, in isolation."""

from __future__ import annotations

from email.mime.image import MIMEImage

from django.core.mail import EmailMessage

from mailkube_django import _payload


def test_attachment_omits_the_content_type_when_unknown():
    assert _payload.attachment("a.txt", b"x", None) == {"filename": "a.txt", "content": b"x"}


def test_attachment_includes_a_known_content_type():
    assert _payload.attachment("a.txt", b"x", "text/plain")["content_type"] == "text/plain"


def test_build_maps_the_core_fields():
    params = _payload.build(EmailMessage("Subject", "Body", "from@x.com", ["a@y.com", "b@y.com"]))

    assert params == {
        "from_": "from@x.com",
        "to": ["a@y.com", "b@y.com"],
        "subject": "Subject",
        "text": "Body",
    }


def test_build_drops_empty_addresses():
    message = EmailMessage("S", "B", "from@x.com", ["a@y.com", ""])
    assert _payload.build(message)["to"] == ["a@y.com"]


def test_build_handles_a_mime_attachment():
    message = EmailMessage("S", "B", "from@x.com", ["a@y.com"])
    image = MIMEImage(b"\x89PNG\r\n\x1a\n", "png")
    image.add_header("Content-Disposition", "attachment", filename="logo.png")
    message.attach(image)

    attached = _payload.build(message)["attachments"][0]
    assert attached["filename"] == "logo.png"
    assert attached["content_type"] == "image/png"


def test_build_omits_optional_fields_that_are_unset():
    params = _payload.build(EmailMessage("S", "B", "from@x.com", ["a@y.com"]))
    for field in ("cc", "bcc", "reply_to", "headers", "attachments", "html"):
        assert field not in params
