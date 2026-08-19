"""Django system checks for common misconfigurations.

These turn two failure modes that would otherwise only surface on the first send into a
``manage.py check`` warning: selecting the Anymail backend without installing the extra, and
forgetting the API key entirely.
"""

from __future__ import annotations

import os
from importlib.util import find_spec
from typing import Any

from django.conf import settings
from django.core.checks import Warning as DjangoWarning

from . import _config

ANYMAIL_BACKEND_PATH = "mailkube_django.anymail_backend.EmailBackend"


def check_configuration(app_configs: Any, **kwargs: Any) -> list[DjangoWarning]:  # noqa: ARG001
    """Report configuration problems for this package's backends.

    Args:
        app_configs: The app configs being checked (unused; this is a project-wide check).
        **kwargs: Additional arguments passed by Django's check framework.

    Returns:
        A list of warnings, empty when the configuration looks usable.
    """
    backend = getattr(settings, "EMAIL_BACKEND", "")
    if not backend.startswith("mailkube_django."):
        return []

    warnings = []
    if backend == ANYMAIL_BACKEND_PATH and not _anymail_installed():
        warnings.append(
            DjangoWarning(
                "EMAIL_BACKEND uses the Anymail backend, but django-anymail is not installed.",
                hint='Install the extra: pip install "mailkube-django[anymail]".',
                id="mailkube_django.W001",
            )
        )
    if not _api_key_configured():
        warnings.append(
            DjangoWarning(
                "No API key is configured, so sending will fail.",
                hint="Set MAILKUBE_API_KEY in settings, or the MAILKUBE_API_KEY environment variable.",
                id="mailkube_django.W002",
            )
        )
    return warnings


def _anymail_installed() -> bool:
    """Return whether ``django-anymail`` can be imported."""
    return find_spec("anymail") is not None


def _api_key_configured() -> bool:
    """Return whether an API key is reachable from settings or the environment."""
    if _config.client_kwargs().get("api_key"):
        return True
    return bool(os.environ.get("MAILKUBE_API_KEY"))
