"""Receive inbound webhooks in a Django view.

The SDK already owns signature verification and event parsing, so this module is
deliberately thin: it adapts an ``HttpRequest`` to the SDK's verifier and dispatches a
Django signal. Do not re-implement the HMAC check or the payload decoding here.

Wire it up::

    from mailkube_django.webhooks import WebhookView

    urlpatterns = [path("webhooks/mailkube/", WebhookView.as_view())]

Then receive events::

    from mailkube import EmailSentEvent
    from mailkube_django.webhooks import webhook_received

    @receiver(webhook_received)
    def handle(sender, event, **kwargs):
        if isinstance(event, EmailSentEvent):
            print(event.data.email_id)

``event`` is a typed :class:`~mailkube.WebhookEvent`. An event type the installed SDK does
not recognize arrives as :class:`~mailkube.UnknownEvent` rather than raising, so a new
platform event never breaks a receiver.
"""

from __future__ import annotations

from typing import Any

import django.dispatch
from django.conf import settings
from django.http import HttpRequest, HttpResponse, JsonResponse
from django.utils.decorators import method_decorator
from django.views import View
from django.views.decorators.csrf import csrf_exempt
from mailkube import SignatureVerificationError, verify

#: Sent once per verified webhook, with the parsed ``event`` (a ``WebhookEvent``).
webhook_received = django.dispatch.Signal()


@method_decorator(csrf_exempt, name="dispatch")
class WebhookView(View):
    """Verify an inbound webhook and dispatch :data:`webhook_received`.

    The signing secret comes from the ``MAILKUBE_WEBHOOK_SECRET`` setting.
    """

    def post(self, request: HttpRequest, *args: Any, **kwargs: Any) -> HttpResponse:  # noqa: ARG002
        """Verify the signature over the raw body, then dispatch the parsed event.

        Args:
            request: The inbound request.
            *args: Unused positional arguments from the URL resolver.
            **kwargs: Unused keyword arguments from the URL resolver.

        Returns:
            ``200`` once the event has been dispatched, ``400`` if verification failed or
            the body is not a readable event.
        """
        secret = getattr(settings, "MAILKUBE_WEBHOOK_SECRET", None)
        if not secret:
            return JsonResponse({"detail": "Webhook secret is not configured."}, status=500)

        try:
            # Verify against request.body, the raw received bytes. Parsing and
            # re-serializing would change them and the signature would not match.
            event = verify(request.body, request.headers, secret)
        except SignatureVerificationError as exc:
            return JsonResponse({"detail": str(exc)}, status=400)
        except ValueError:
            # pydantic's ValidationError is a ValueError, so this catches a signed body the
            # SDK cannot read without importing pydantic here. The event models are lenient
            # by design, so reaching this means the payload really is malformed: 400,
            # because the request is what is wrong. The detail is fixed rather than the
            # exception text, which describes the SDK's internals.
            return JsonResponse({"detail": "Malformed webhook payload."}, status=400)

        webhook_received.send(sender=self.__class__, event=event)
        return JsonResponse({"detail": "ok"})
