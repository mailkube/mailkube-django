"""URL configuration for the test suite: just the webhook endpoint."""

from __future__ import annotations

from django.urls import path

from mailkube_django.webhooks import WebhookView

urlpatterns = [path("webhooks/", WebhookView.as_view(), name="webhook")]
