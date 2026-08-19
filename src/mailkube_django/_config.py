"""Resolve SDK configuration from Django settings.

One home for "which Django setting maps to which SDK constructor argument", so the two
backends and the system checks cannot disagree about where the API key comes from.

Anything unset here falls through to the SDK, which resolves its own environment variables
(``MAILKUBE_API_KEY``, ``MAILKUBE_BASE_URL``) and raises an actionable error if the key is
missing. This package deliberately does not re-implement that resolution or re-validate it.
"""

from __future__ import annotations

from typing import Any

from django.conf import settings

from ._version import __version__

#: Django setting name -> SDK constructor keyword.
SETTING_MAP = {
    "MAILKUBE_API_KEY": "api_key",
    "MAILKUBE_BASE_URL": "base_url",
    "MAILKUBE_TIMEOUT": "timeout",
}


def user_agent_suffix() -> str:
    """Return this package's own ``name/version`` token for the SDK's User-Agent.

    The version is read from the installed distribution rather than written here. A literal
    would be a second source of truth that the release process does not update, so it would
    go stale on the first release and stay wrong for every one after it.

    The SDK's own token stays leading, so the header reads
    ``mailkube-python/1.5.0 mailkube-django/0.1.0``.

    Returns:
        The suffix token.
    """
    return f"mailkube-django/{__version__}"


def client_kwargs(**overrides: Any) -> dict[str, Any]:
    """Return SDK client keyword arguments from Django settings.

    A setting that is absent or ``None`` is omitted entirely rather than passed as ``None``,
    so the SDK's own environment-variable fallbacks still apply.

    Args:
        **overrides: Explicit values that win over the Django settings.

    Returns:
        Keyword arguments for the SDK client constructor.
    """
    resolved: dict[str, Any] = {}
    for setting_name, kwarg in SETTING_MAP.items():
        value = getattr(settings, setting_name, None)
        if value is not None:
            resolved[kwarg] = value
    resolved.update({key: value for key, value in overrides.items() if value is not None})
    return resolved


def client_arguments(**overrides: Any) -> dict[str, Any]:
    """Return the full SDK client keyword arguments, including this package's identity.

    Separate from :func:`client_kwargs`, which stays a pure "which Django setting maps to
    which SDK keyword" mapping: the startup checks probe that mapping for a configured API
    key, and folding an always-present suffix into it would make an unconfigured project
    look configured.

    Args:
        **overrides: Explicit values that win over the Django settings.

    Returns:
        Keyword arguments for the SDK client constructor.
    """
    # Identify this package in the User-Agent once, here. Doing it at a call site would mean
    # whichever call site remembered, and the two backends would drift apart.
    return {**client_kwargs(**overrides), "user_agent_suffix": user_agent_suffix()}
