"""The Django app config.

Adding this package to ``INSTALLED_APPS`` is **optional**: Django loads an email backend
from its dotted path, so sending works without it. Installing the app registers the system
checks in :mod:`mailkube_django.checks`, which is the only reason to bother.

There are deliberately no models and there is no ``migrations/`` package. This integration
holds no persistent state, and needing some would mean it belongs in a different package.
"""

from __future__ import annotations

from django.apps import AppConfig
from django.core.checks import register


class MailkubeDjangoConfig(AppConfig):
    """App config that registers this package's system checks."""

    name = "mailkube_django"
    verbose_name = "mailkube-django"

    def ready(self) -> None:
        """Register the configuration checks with Django's check framework."""
        from .checks import check_configuration  # noqa: PLC0415 — apps are not loaded at import time

        register(check_configuration)
