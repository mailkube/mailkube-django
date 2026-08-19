"""The SDK client lifecycle, shared by both backends.

Django's email-backend contract already has ``open()``/``close()``, and the SDK client is a
context manager over a connection pool, so the two map onto each other directly. Both
backends need exactly that, so it is written once here rather than twice.

There is deliberately no module-level client singleton: it would leak a connection pool
across settings changes and break test isolation.
"""

from __future__ import annotations

from mailkube import Mailkube, MailkubeError

from . import _config


class SDKClientMixin:
    """Create, expose and release the SDK client for an email backend.

    The host backend must set :attr:`_client_overrides` in its constructor and provides
    ``fail_silently`` (both Django's ``BaseEmailBackend`` and Anymail's backend do).
    """

    fail_silently: bool
    _client_overrides: dict[str, object]
    client: Mailkube | None = None

    def open(self) -> bool:
        """Create the SDK client if it does not exist yet.

        Returns:
            ``True`` if this call created the client, matching Django's convention.
        """
        if self.client is not None:
            return False
        try:
            self.client = Mailkube(**_config.client_arguments(**self._client_overrides))
        except MailkubeError:
            if not self.fail_silently:
                raise
            return False
        return True

    def close(self) -> None:
        """Release the SDK client's connection pool."""
        if self.client is None:
            return
        try:
            self.client.close()
        finally:
            self.client = None
