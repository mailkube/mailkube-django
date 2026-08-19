# Django Integration

Load this when touching either backend, the payload mapping, the settings surface, the
webhook view, or the system checks.

The framework-neutral rules — thin adapter, one HTTP path, one payload module, one config
module, no persistent state, raw-body webhook verification, error translation, no real host
app in tests — live in [`INTEGRATION_CONTRACT.md`](INTEGRATION_CONTRACT.md) and are not
repeated here. **This file covers only the Django realization**, including the deviations the
integration contract requires be recorded locally.

## The two-backend contract

This is the one structural thing about this package that is not in the shared contract: it ships
**two** entry points in one distribution, and both must keep working.

- **`backends.EmailBackend` must never import `anymail`**, directly or transitively. Users
  who install without the `[anymail]` extra depend on that. `tests/test_backends.py` asserts
  it rather than trusting it.
- **`django-anymail` stays in `[project.optional-dependencies]`**, never in `dependencies`.
  It is also in the dev group so the Anymail tests run locally, and the `zero-extra` CI job runs
  the suite *without* the extra to prove the zero-extra path still imports.
- **`__init__.py` imports neither backend.** Django loads a backend from its dotted path, so
  eager re-exports would drag `anymail` into every install.
- Both backends are selectable by `EMAIL_BACKEND` alone. **`INSTALLED_APPS` is optional** and
  only registers the system checks.

## Realizing "one HTTP path" in Anymail

`anymail_backend` subclasses `AnymailBaseBackend`, **not** `AnymailRequestsBackend`. The
requests base is exactly the "framework base class that opens its own HTTP client" the
integration contract forbids: it would re-serialize the payload itself and give this package a
second wire format. Instead the Anymail payload's `set_*` methods accumulate **SDK keyword
arguments** and `post_to_esp` calls the same SDK verb the standalone backend uses.

The error-translation rule lands here concretely: `post_to_esp` **must** turn `MailkubeError`
into `AnymailAPIError`, because Anymail's `fail_silently` only suppresses its own error types.
A test pins it.

## What belongs where

| Concern | Home |
|---|---|
| Django settings to SDK constructor arguments | `_config.py` |
| SDK client creation and release | `_lifecycle.py` |
| Django message to SDK keyword arguments | `_payload.py` |
| Anymail-normalized values to SDK keyword arguments | `anymail_backend.MailkubePayload` |
| Wire format, auth, retries, errors | the SDK, not this package |

The one conversion both backends genuinely share, turning a single attachment into the SDK's
shape, is `_payload.attachment`. This is the integration contract's "share the conversion they
truly have in common and no more" applied: their inputs differ (raw Django message vs
Anymail-normalized values), so forcing them through one function would obscure both.

## Django specifics

- **Both backends are synchronous, and use the SDK's sync client.** Django's
  `BaseEmailBackend.send_messages()` and Anymail's `post_to_esp()` are both synchronous hooks,
  and Django offers no async email backend API to implement. Per the integration contract's
  flavour rule, **never reach for `AsyncMailkube` here**, and never wrap it in `asyncio.run()`:
  under ASGI that runs inside a live event loop and raises.
- **The client lifecycle lives once in `_lifecycle.SDKClientMixin`**, mapping Django's
  `open()`/`close()` backend protocol onto the SDK's context-manager lifecycle. Do not
  re-implement `open()`/`close()` in a backend, and do not introduce a module-level client
  singleton: it would leak a connection pool across settings changes and break test isolation.
- **The webhook view reads `request.body`**, which is Django's accessor for the raw received
  bytes.
- **`tests/settings.py` is a minimal settings module and `DATABASES` is deliberately empty**,
  which is how the contract's no-database rule is enforced here.
- Tests exercise the **real** SDK over an `httpx.MockTransport` (see `tests/conftest.py`).
