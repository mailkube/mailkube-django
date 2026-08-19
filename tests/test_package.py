"""Packaging guards: the version, the typing marker, and the settings mapping."""

from __future__ import annotations

import re
from importlib.metadata import version
from pathlib import Path

import httpx
from django.test import override_settings
from mailkube import Mailkube

import mailkube_django
from conftest import capturing_handler
from mailkube_django import _config


def test_version_matches_the_installed_distribution():
    assert mailkube_django.__version__ == version("mailkube-django")


def test_py_typed_marker_ships():
    assert (Path(mailkube_django.__file__).parent / "py.typed").is_file()


@override_settings(MAILKUBE_API_KEY="mk_settings", MAILKUBE_BASE_URL="https://staging.example.com/v1/")
def test_settings_map_onto_sdk_constructor_arguments():
    assert _config.client_kwargs() == {
        "api_key": "mk_settings",
        "base_url": "https://staging.example.com/v1/",
    }


@override_settings(MAILKUBE_API_KEY=None)
def test_an_unset_setting_is_omitted_so_the_sdk_env_fallback_still_applies():
    assert "api_key" not in _config.client_kwargs()


@override_settings(MAILKUBE_API_KEY="mk_settings")
def test_an_explicit_override_wins_over_settings():
    assert _config.client_kwargs(api_key="mk_override")["api_key"] == "mk_override"


@override_settings(MAILKUBE_API_KEY="mk_settings")
def test_a_none_override_does_not_erase_the_setting():
    assert _config.client_kwargs(api_key=None)["api_key"] == "mk_settings"


def test_the_user_agent_suffix_names_this_package_and_is_not_a_literal_version():
    suffix = _config.user_agent_suffix()

    assert suffix.startswith("mailkube-django/")

    # Read from the installed distribution, which is what the release process updates. A literal
    # would be a second source of truth and would report the version this file was written at,
    # forever.
    _, _, reported = suffix.partition("/")
    assert reported == version("mailkube-django")


@override_settings(MAILKUBE_API_KEY="mk_settings")
def test_the_client_arguments_carry_the_suffix_but_the_settings_map_does_not():
    # The two are deliberately separate. `client_kwargs` answers "which Django setting is set",
    # which is what the startup checks probe for a configured API key; folding an always-present
    # suffix into it would make an unconfigured project look configured.
    assert "user_agent_suffix" not in _config.client_kwargs()
    assert _config.client_arguments()["user_agent_suffix"] == _config.user_agent_suffix()


@override_settings(MAILKUBE_API_KEY="mk_test")
def test_the_suffix_reaches_the_wire_after_the_sdks_own_token():
    # The real client over a stub transport, so this asserts what the SDK actually composes
    # rather than what this package hands it.
    captured: dict = {}
    http = httpx.Client(transport=httpx.MockTransport(capturing_handler(captured)))
    client = Mailkube(**_config.client_arguments(), http_client=http)
    client.emails.send(from_="a@x.test", to="b@y.test", subject="s", text="t")

    agent = captured["headers"]["user-agent"]

    # Asserted as "the SDK leads, this package trails", not against a literal SDK token: what
    # that token says is the SDK's business, and pinning it here would make this test fail on an
    # SDK release that renamed itself, reporting a bug in the wrong repository.
    assert re.match(r"\A\S+/\S+ ", agent)
    assert agent.endswith(f" {_config.user_agent_suffix()}")
