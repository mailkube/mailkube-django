"""Minimal Django settings for the test suite.

Deliberately tiny: this package has no models and no migrations, so the tests need a
configured Django, not a database.
"""

from __future__ import annotations

SECRET_KEY = "test-only-not-a-secret"
USE_TZ = True
INSTALLED_APPS = ["mailkube_django"]
DATABASES: dict[str, object] = {}
ROOT_URLCONF = "urls"

EMAIL_BACKEND = "mailkube_django.backends.EmailBackend"
MAILKUBE_API_KEY = "mk_test"
MAILKUBE_WEBHOOK_SECRET = "whsec_test"
