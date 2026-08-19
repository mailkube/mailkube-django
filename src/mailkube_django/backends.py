"""The standalone Django email backend.

This is the zero-extra-dependency path: it needs only Django and the mailkube SDK.
Point Django at it and nothing else changes::

    EMAIL_BACKEND = "mailkube_django.backends.EmailBackend"

**This module must never import ``anymail``**, directly or transitively. Users who install
without the ``[anymail]`` extra rely on that. See ``.rules/DJANGO_INTEGRATION.md``.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from django.core.mail.backends.base import BaseEmailBackend
from mailkube import MailkubeError

from . import _payload
from ._lifecycle import SDKClientMixin

if TYPE_CHECKING:
    from collections.abc import Sequence

    from django.core.mail import EmailMessage


class EmailBackend(SDKClientMixin, BaseEmailBackend):
    """Send Django mail through the mailkube API.

    Example:
        >>> EMAIL_BACKEND = "mailkube_django.backends.EmailBackend"
        >>> MAILKUBE_API_KEY = "mk_..."
    """

    def __init__(
        self,
        *,
        fail_silently: bool = False,
        api_key: str | None = None,
        base_url: str | None = None,
        timeout: float | None = None,
        **kwargs: object,  # noqa: ARG002 — Django may pass extra backend options
    ) -> None:
        """Create the backend.

        Args:
            fail_silently: Swallow send errors instead of raising, per Django's contract.
            api_key: Override the ``MAILKUBE_API_KEY`` setting.
            base_url: Override the ``MAILKUBE_BASE_URL`` setting.
            timeout: Override the ``MAILKUBE_TIMEOUT`` setting.
            **kwargs: Accepted and ignored, as Django may pass extra backend options.
        """
        super().__init__(fail_silently=fail_silently)
        self._client_overrides = {"api_key": api_key, "base_url": base_url, "timeout": timeout}

    def send_messages(self, email_messages: Sequence[EmailMessage]) -> int:
        """Send each message, returning how many the API accepted.

        Args:
            email_messages: The messages Django wants sent.

        Returns:
            The number of messages the API accepted.

        Raises:
            MailkubeError: On any send or configuration failure, unless ``fail_silently``.
        """
        if not email_messages:
            return 0

        created = self.open()
        if self.client is None:
            return 0
        try:
            return sum(1 for message in email_messages if self._send(message))
        finally:
            if created:
                self.close()

    def _send(self, message: EmailMessage) -> bool:
        """Send one message, honouring ``fail_silently``.

        Args:
            message: The message to send.

        Returns:
            ``True`` when the API accepted the message.

        Raises:
            MailkubeError: On failure, unless ``fail_silently`` is set.
        """
        if not message.recipients():
            return False
        try:
            self.client.emails.send(**_payload.build(message))  # type: ignore[union-attr]
        except MailkubeError:
            if not self.fail_silently:
                raise
            return False
        return True
