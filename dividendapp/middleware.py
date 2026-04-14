"""Session-backed user preferences: theme + currency."""
from __future__ import annotations

from django.conf import settings


class PreferencesMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        session = request.session
        if "theme" not in session:
            session["theme"] = "dark"
        currency = session.get("currency")
        if currency not in settings.SUPPORTED_CURRENCIES:
            session["currency"] = settings.DEFAULT_CURRENCY
        return self.get_response(request)
