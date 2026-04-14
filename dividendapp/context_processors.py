from django.conf import settings


def preferences(request):
    currency = request.session.get("currency", settings.DEFAULT_CURRENCY)
    return {
        "theme": request.session.get("theme", "dark"),
        "currency": currency,
        "currency_symbol": settings.SUPPORTED_CURRENCIES[currency]["symbol"],
        "supported_currencies": settings.SUPPORTED_CURRENCIES,
    }
