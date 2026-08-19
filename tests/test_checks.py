"""System checks for the two misconfigurations that otherwise surface only on first send."""

from __future__ import annotations

from django.test import override_settings

from mailkube_django.checks import check_configuration


@override_settings(EMAIL_BACKEND="django.core.mail.backends.locmem.EmailBackend")
def test_another_backend_is_none_of_our_business():
    assert check_configuration(None) == []


@override_settings(EMAIL_BACKEND="mailkube_django.backends.EmailBackend")
def test_a_configured_standalone_backend_is_clean():
    assert check_configuration(None) == []


@override_settings(EMAIL_BACKEND="mailkube_django.backends.EmailBackend", MAILKUBE_API_KEY=None)
def test_a_missing_api_key_is_reported(monkeypatch):
    monkeypatch.delenv("MAILKUBE_API_KEY", raising=False)
    assert [warning.id for warning in check_configuration(None)] == ["mailkube_django.W002"]


@override_settings(EMAIL_BACKEND="mailkube_django.backends.EmailBackend", MAILKUBE_API_KEY=None)
def test_the_environment_variable_satisfies_the_api_key_check(monkeypatch):
    monkeypatch.setenv("MAILKUBE_API_KEY", "mk_from_env")
    assert check_configuration(None) == []


@override_settings(EMAIL_BACKEND="mailkube_django.anymail_backend.EmailBackend")
def test_the_anymail_backend_warns_when_the_extra_is_missing(monkeypatch):
    monkeypatch.setattr("mailkube_django.checks._anymail_installed", lambda: False)
    assert "mailkube_django.W001" in [warning.id for warning in check_configuration(None)]
