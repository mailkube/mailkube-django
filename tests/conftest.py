"""Shared test helpers.

The SDK client is swapped for one backed by an ``httpx.MockTransport``, so the tests
exercise the **real** SDK (its serialization, its error mapping) with zero network access.
Faking the SDK itself would only prove the tests agree with themselves.
"""

from __future__ import annotations

import json
from collections.abc import Callable

import httpx
from mailkube import Mailkube

from mailkube_django import _lifecycle

Handler = Callable[[httpx.Request], httpx.Response]

ACCEPTED = {"id": "abc123", "message_id": "<abc123@msg.example.com>"}


def ok_handler(request: httpx.Request) -> httpx.Response:
    return httpx.Response(200, json=ACCEPTED)


def error_handler(status: int, name: str = "validation_error") -> Handler:
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(status, json={"name": name, "message": "nope"})

    return handler


def capturing_handler(captured: dict, status: int = 200, payload: object = None) -> Handler:
    def handler(request: httpx.Request) -> httpx.Response:
        captured["url"] = str(request.url)
        captured["headers"] = dict(request.headers)
        captured["body"] = json.loads(request.content) if request.content else None
        return httpx.Response(status, json=payload if payload is not None else ACCEPTED)

    return handler


def patch_sdk(monkeypatch, handler: Handler) -> dict:
    """Route every SDK client the backends build through ``handler``.

    Returns:
        A dict recording the keyword arguments the backend passed to the SDK.
    """
    seen: dict = {}

    def factory(**kwargs):
        seen["kwargs"] = kwargs
        http = httpx.Client(transport=httpx.MockTransport(handler))
        return Mailkube(api_key=kwargs.get("api_key") or "mk_test", http_client=http)

    monkeypatch.setattr(_lifecycle, "Mailkube", factory)
    return seen
