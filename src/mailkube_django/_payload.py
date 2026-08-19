"""Translate a Django message into mailkube SDK keyword arguments.

Both backends end up calling the same SDK verb, so **the wire format lives in exactly one
place: the SDK**. Neither backend builds JSON. That is what keeps the two of them from
drifting, and it is why adding a field to the API only ever needs a change in the SDK.

What the two backends do *not* share is their input: the standalone backend receives a raw
``django.core.mail.EmailMessage``, while the Anymail backend receives values already
normalized by Anymail's payload setters (parsed addresses, prepped attachments). The
genuinely common step, converting one attachment into the SDK's ``Attachment`` shape, lives
here and is called by both.
"""

from __future__ import annotations

from email.mime.base import MIMEBase
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from django.core.mail import EmailMessage

_HTML_SUBTYPE = "html"


def attachment(filename: str, content: str | bytes, mimetype: str | None) -> dict[str, Any]:
    """Return one attachment in the SDK's ``Attachment`` shape.

    A ``str`` is always encoded to ``bytes`` first. The SDK treats ``bytes`` as raw content
    to base64-encode and a ``str`` as *already* base64-encoded, but Django hands us decoded
    text for ``text/*`` attachments, which is raw content and not base64. Passing it through
    unchanged would ship the literal text in a field the API decodes as base64.

    This is the one conversion both backends share.

    Args:
        filename: The attached file's name.
        content: The file content, as raw text or bytes.
        mimetype: The declared MIME type, if any.

    Returns:
        An SDK attachment mapping.
    """
    data = content.encode("utf-8") if isinstance(content, str) else content
    item: dict[str, Any] = {"filename": filename, "content": data}
    if mimetype:
        item["content_type"] = mimetype
    return item


def _addresses(values: list[str]) -> list[str]:
    """Return a clean address list, dropping empties."""
    return [value for value in values if value]


def _attachments(message: EmailMessage) -> list[dict[str, Any]]:
    """Convert Django's attachment tuples and MIME parts into SDK attachments."""
    items: list[dict[str, Any]] = []
    for entry in message.attachments:
        if isinstance(entry, MIMEBase):
            decoded = entry.get_payload(decode=True)
            items.append(
                attachment(
                    entry.get_filename() or "attachment",
                    decoded if isinstance(decoded, bytes) else b"",
                    entry.get_content_type(),
                )
            )
        else:
            filename, content, mimetype = entry
            items.append(attachment(filename, content, mimetype))
    return items


def _bodies(message: EmailMessage) -> tuple[str | None, str | None]:
    """Return the ``(text, html)`` bodies of a Django message.

    Honours ``content_subtype == "html"`` for a plain ``EmailMessage``, and picks the
    ``text/html`` alternative off an ``EmailMultiAlternatives``.
    """
    text: str | None = None
    html: str | None = None
    if message.content_subtype == _HTML_SUBTYPE:
        html = str(message.body)
    else:
        text = str(message.body)

    for content, mimetype in getattr(message, "alternatives", []) or []:
        if mimetype == "text/html":
            html = str(content)
    return text, html


def build(message: EmailMessage) -> dict[str, Any]:
    """Return the SDK ``emails.send`` keyword arguments for a Django message.

    Args:
        message: The Django ``EmailMessage`` or ``EmailMultiAlternatives`` to translate.

    Returns:
        Keyword arguments ready to splat into the SDK's send verb.
    """
    text, html = _bodies(message)
    params: dict[str, Any] = {
        "from_": message.from_email,
        "to": _addresses(list(message.to)),
        "subject": str(message.subject),
    }
    if text is not None:
        params["text"] = text
    if html is not None:
        params["html"] = html
    if message.cc:
        params["cc"] = _addresses(list(message.cc))
    if message.bcc:
        params["bcc"] = _addresses(list(message.bcc))
    if message.reply_to:
        params["reply_to"] = _addresses(list(message.reply_to))
    if message.extra_headers:
        params["headers"] = dict(message.extra_headers)
    if message.attachments:
        params["attachments"] = _attachments(message)
    return params
