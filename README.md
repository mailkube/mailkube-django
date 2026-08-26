# mailkube-django

[![CI](https://github.com/mailkube/mailkube-django/actions/workflows/ci.yml/badge.svg)](https://github.com/mailkube/mailkube-django/actions/workflows/ci.yml)
[![PyPI](https://img.shields.io/pypi/v/mailkube-django)](https://pypi.org/project/mailkube-django/)
[![License: Apache 2.0](https://img.shields.io/badge/license-Apache%202.0-blue.svg)](LICENSE)
[![Python](https://img.shields.io/badge/python-3.12%2B-blue)](pyproject.toml)
[![Django](https://img.shields.io/badge/django-5.2%2B-0C4B33)](pyproject.toml)
[![Code of Conduct](https://img.shields.io/badge/Contributor%20Covenant-2.1-purple.svg)](CODE_OF_CONDUCT.md)

Django email backend for mailkube.

## Which backend?

Two backends ship in one distribution. Pick one with `EMAIL_BACKEND`.

| | `backends.EmailBackend` | `anymail_backend.EmailBackend` |
|---|---|---|
| Extra dependencies | **none** beyond Django + the SDK | `django-anymail` |
| `send_mail`, `EmailMessage`, `EmailMultiAlternatives` | yes | yes |
| Attachments, cc/bcc, reply-to, custom headers | yes | yes |
| Tags, scheduled send, templates, `esp_extra` | | yes |
| `pre_send` / `post_send` signals, `anymail_status` | | yes |
| Portable across ESPs | | yes |

Choose the standalone backend if you just want Django mail to go through mailkube. Choose
the Anymail one if you already use Anymail, want its extra message features, or want to keep
the option of swapping providers.

Both send through the same SDK, so the wire behaviour is identical.

## Install

```bash
pip install mailkube-django
# or, for the Anymail backend:
pip install "mailkube-django[anymail]"
```

## Standalone backend

```python
# settings.py
EMAIL_BACKEND = "mailkube_django.backends.EmailBackend"
MAILKUBE_API_KEY = "mk_..."  # or the MAILKUBE_API_KEY env var
DEFAULT_FROM_EMAIL = "Acme <hello@yourdomain.com>"
```

```python
from django.core.mail import send_mail

send_mail("Hello world", "It works!", None, ["customer@example.com"])
```

Optional settings: `MAILKUBE_BASE_URL` and `MAILKUBE_TIMEOUT`. Anything left unset falls
through to the SDK, which reads `MAILKUBE_API_KEY` / `MAILKUBE_BASE_URL` from the environment.

## Anymail backend

```python
# settings.py
EMAIL_BACKEND = "mailkube_django.anymail_backend.EmailBackend"
ANYMAIL = {"MAILKUBE_API_KEY": "mk_..."}
```

```python
from django.core.mail import EmailMultiAlternatives

message = EmailMultiAlternatives("Hello", "It works!", None, ["customer@example.com"])
message.attach_alternative("<p>It works!</p>", "text/html")
message.tags = ["welcome"]
message.send()

message.anymail_status.recipients["customer@example.com"].message_id
```

Supported Anymail features: `tags`, `send_at`, `template_id`, `merge_global_data`,
`esp_extra`, the send signals, and per-recipient `anymail_status`. Features the API has no
equivalent for (such as `metadata` and per-recipient `merge_data`) raise Anymail's usual
unsupported-feature error rather than being silently dropped.

## Webhooks

```python
# urls.py
from mailkube_django.webhooks import WebhookView

urlpatterns = [path("webhooks/mailkube/", WebhookView.as_view())]
```

```python
# settings.py
MAILKUBE_WEBHOOK_SECRET = "whsec_..."
```

```python
from django.dispatch import receiver
from mailkube import EmailSentEvent
from mailkube_django.webhooks import webhook_received


@receiver(webhook_received)
def handle(sender, event, **kwargs):
    if isinstance(event, EmailSentEvent):
        print(event.data.email_id, event.data.sent.recipient)
```

Signatures are verified by the SDK over the raw request body before the signal fires, and
`event` is one of the SDK's typed `WebhookEvent` models. An event type your installed SDK
version does not know arrives as `UnknownEvent` with its raw `data` intact, so a new
platform event never breaks a receiver. A delivery whose signature does not check out, or
whose body is not a readable event, gets a `400` and no signal.

## Checks

Add `"mailkube_django"` to `INSTALLED_APPS` (optional) to have `manage.py check` warn
about a missing API key or a selected Anymail backend without the extra installed. Sending
works either way; the app registers nothing but those checks, and there are no models or
migrations.

## Contributing

See [CONTRIBUTING.md](CONTRIBUTING.md) for the development setup and the quality gates every change
must pass. Conventions live in [`.rules/`](.rules/), indexed by [AGENTS.md](AGENTS.md). Security
issues: see [SECURITY.md](SECURITY.md).

## License

[Apache-2.0](LICENSE) © 2026 Mail Tactic Corporation
