"""The Anymail-compatible Django email backend.

Requires the ``anymail`` extra::

    pip install mailkube-django[anymail]
    EMAIL_BACKEND = "mailkube_django.anymail_backend.EmailBackend"
    ANYMAIL = {"MAILKUBE_API_KEY": "mk_..."}

``anymail`` is imported **only here**, never from ``__init__`` or ``backends``, so the
zero-extra-dependency install path never touches it.

Why this subclasses ``AnymailBaseBackend`` and not ``AnymailRequestsBackend``: the requests
base would open a second HTTP path and re-implement the wire format in a payload
serializer, which is exactly the duplication that lets two backends drift. Instead the
payload setters accumulate **SDK keyword arguments** and ``post_to_esp`` calls the same SDK
verb the standalone backend uses, so the wire format has one owner.

What Anymail adds over the standalone backend: normalized addresses and attachments,
``tags``, ``send_at``, ``template_id``, ``merge_global_data``, ``esp_extra``, the
pre/post-send signals, and per-recipient ``anymail_status``.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

from anymail.backends.base import AnymailBaseBackend, BasePayload
from anymail.exceptions import AnymailAPIError
from anymail.message import AnymailRecipientStatus
from anymail.utils import get_anymail_setting
from mailkube import MailkubeError

from . import _payload
from ._lifecycle import SDKClientMixin

if TYPE_CHECKING:
    from django.core.mail import EmailMessage
    from mailkube import Email


class EmailBackend(SDKClientMixin, AnymailBaseBackend):
    """Anymail ESP backend that sends through the mailkube SDK."""

    esp_name = "Mailkube"

    def __init__(self, **kwargs: Any) -> None:
        """Read Anymail settings and prepare the SDK client configuration.

        Args:
            **kwargs: Anymail backend options, including an optional ``api_key``.
        """
        esp_name = self.esp_name
        api_key = get_anymail_setting("api_key", esp_name=esp_name, kwargs=kwargs, default=None, allow_bare=True)
        base_url = get_anymail_setting("api_url", esp_name=esp_name, kwargs=kwargs, default=None, allow_bare=False)
        super().__init__(**kwargs)
        self._client_overrides = {"api_key": api_key, "base_url": base_url, "timeout": None}

    def build_message_payload(self, message: EmailMessage, defaults: dict[str, Any]) -> MailkubePayload:
        """Return the payload collecting this message's SDK keyword arguments."""
        return MailkubePayload(message, defaults, self)

    def post_to_esp(self, payload: MailkubePayload, message: EmailMessage) -> Email:
        """Send the payload through the SDK.

        Args:
            payload: The built payload.
            message: The original Django message.

        Returns:
            The SDK's send result.

        Raises:
            AnymailAPIError: If the SDK reports any failure. Anymail's ``fail_silently``
                handling only recognizes its own error types, so SDK errors are translated.
        """
        try:
            return self.client.emails.send(**payload.data)  # type: ignore[union-attr]
        except MailkubeError as exc:
            raise AnymailAPIError(str(exc), backend=self, email_message=message, payload=payload) from exc

    def parse_recipient_status(
        self,
        response: Email,
        payload: MailkubePayload,
        message: EmailMessage,  # noqa: ARG002 — signature fixed by Anymail
    ) -> dict[str, AnymailRecipientStatus]:
        """Report every recipient as queued under the accepted message's id.

        The API accepts a send as a whole rather than per recipient, so each address shares
        the returned id. A scheduled send is also reported as ``"queued"``: Anymail's status
        vocabulary is a closed set that has no "scheduled" member, and inventing one raises.
        Callers distinguish the two through the API, not through Anymail's status.

        Args:
            response: The SDK send result.
            payload: The payload that was sent.
            message: The original Django message.

        Returns:
            A mapping of address to :class:`AnymailRecipientStatus`.
        """
        status = AnymailRecipientStatus
        return {address: status(message_id=response.id, status="queued") for address in payload.recipients}


class MailkubePayload(BasePayload):
    """Collect Anymail's normalized message values as SDK keyword arguments."""

    def init_payload(self) -> None:
        """Start with an empty parameter set and no recorded recipients."""
        self.data: dict[str, Any] = {}
        self.recipients: list[str] = []

    def set_from_email(self, email: Any) -> None:
        """Set the sender, preserving any display name."""
        self.data["from_"] = email.address

    def set_recipients(self, recipient_type: str, emails: list[Any]) -> None:
        """Set ``to``/``cc``/``bcc`` and record the addresses for status reporting."""
        if emails:
            self.data[recipient_type] = [email.address for email in emails]
            self.recipients += [email.addr_spec for email in emails]

    def set_subject(self, subject: str) -> None:
        """Set the subject line."""
        self.data["subject"] = subject

    def set_reply_to(self, emails: list[Any]) -> None:
        """Set the Reply-To addresses."""
        if emails:
            self.data["reply_to"] = [email.address for email in emails]

    def set_extra_headers(self, headers: dict[str, Any]) -> None:
        """Set custom message headers."""
        if headers:
            self.data["headers"] = dict(headers)

    def set_text_body(self, body: str) -> None:
        """Set the plain-text body."""
        if body:
            self.data["text"] = body

    def set_html_body(self, body: str) -> None:
        """Set the HTML body."""
        if body:
            self.data["html"] = body

    def set_attachments(self, attachments: list[Any]) -> None:
        """Convert Anymail's prepped attachments into SDK attachments."""
        if attachments:
            self.data["attachments"] = [
                _payload.attachment(item.name or "attachment", item.content, item.mimetype) for item in attachments
            ]

    def set_tags(self, tags: list[str]) -> None:
        """Map Anymail's flat tag list onto the API's name/value tags."""
        if tags:
            self.data["tags"] = [{"name": tag, "value": ""} for tag in tags]

    def set_send_at(self, send_at: Any) -> None:
        """Schedule the send instead of delivering it now."""
        self.data["scheduled_at"] = send_at

    def set_template_id(self, template_id: str) -> None:
        """Render a saved template instead of raw content."""
        self.data["template_id"] = template_id

    def set_merge_global_data(self, merge_global_data: dict[str, Any]) -> None:
        """Supply the template's variable values."""
        self.data["variables"] = dict(merge_global_data)

    def set_esp_extra(self, extra: dict[str, Any]) -> None:
        """Merge caller-supplied API parameters that have no Anymail equivalent."""
        self.data.update(extra)
