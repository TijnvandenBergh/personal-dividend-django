"""Django settings for personal-dividend-app (Python/Django port)."""
from __future__ import annotations

import os
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent

SECRET_KEY = os.environ.get("SECRET_KEY", "dev-secret-change-me")
DEBUG = os.environ.get("DJANGO_DEBUG", "1") == "1"

# Space-separated list, e.g. "localhost 127.0.0.1 app.example.com".
ALLOWED_HOSTS = os.environ.get(
    "ALLOWED_HOSTS", "localhost 127.0.0.1 0.0.0.0 [::1] app web"
).split()

CSRF_TRUSTED_ORIGINS = [
    o for o in os.environ.get(
        "CSRF_TRUSTED_ORIGINS",
        "http://localhost:8000 http://127.0.0.1:8000",
    ).split() if o
]

INSTALLED_APPS = [
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",
    "accounts",
    "dividends",
]

MIDDLEWARE = [
    "django.middleware.security.SecurityMiddleware",
    "whitenoise.middleware.WhiteNoiseMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.locale.LocaleMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
    "dividendapp.middleware.PreferencesMiddleware",
]

ROOT_URLCONF = "dividendapp.urls"

TEMPLATES = [
    {
        "BACKEND": "django.template.backends.django.DjangoTemplates",
        "DIRS": [BASE_DIR / "templates"],
        "APP_DIRS": True,
        "OPTIONS": {
            "context_processors": [
                "django.template.context_processors.request",
                "django.template.context_processors.i18n",
                "django.contrib.auth.context_processors.auth",
                "django.contrib.messages.context_processors.messages",
                "dividendapp.context_processors.preferences",
            ],
        },
    },
]

WSGI_APPLICATION = "dividendapp.wsgi.application"

DATABASES = {
    "default": {
        "ENGINE": "django.db.backends.sqlite3",
        "NAME": os.environ.get("DB_FILE", str(BASE_DIR / "app.db")),
    }
}

AUTH_PASSWORD_VALIDATORS = [
    {"NAME": "django.contrib.auth.password_validation.MinimumLengthValidator",
     "OPTIONS": {"min_length": 8}},
]

LANGUAGE_CODE = "en"
LANGUAGES = [("en", "English"), ("nl", "Nederlands")]
LOCALE_PATHS = [BASE_DIR / "locale"]
TIME_ZONE = "UTC"
USE_I18N = True
USE_TZ = True

STATIC_URL = "/static/"
STATICFILES_DIRS = [BASE_DIR / "static"]
STATIC_ROOT = BASE_DIR / "staticfiles"
STATICFILES_STORAGE = (
    "whitenoise.storage.CompressedManifestStaticFilesStorage"
    if not DEBUG
    else "django.contrib.staticfiles.storage.StaticFilesStorage"
)

DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"

# Session / security
SESSION_COOKIE_HTTPONLY = True
SESSION_COOKIE_SAMESITE = "Lax"
SESSION_COOKIE_SECURE = not DEBUG and os.environ.get("SESSION_COOKIE_SECURE", "0") == "1"
SESSION_COOKIE_AGE = 7 * 24 * 60 * 60

LOGIN_URL = "accounts:login"
LOGIN_REDIRECT_URL = "dividends:dashboard"
LOGOUT_REDIRECT_URL = "accounts:login"

# Supported currencies
SUPPORTED_CURRENCIES = {
    "EUR": {"symbol": "€", "name": "Euro"},
    "USD": {"symbol": "$", "name": "US Dollar"},
    "GBP": {"symbol": "£", "name": "British Pound"},
}
DEFAULT_CURRENCY = "EUR"
# Simple static FX rates relative to EUR (1 EUR = X). Replace with live provider later.
FX_RATES_FROM_EUR = {"EUR": 1.0, "USD": 1.08, "GBP": 0.86}
