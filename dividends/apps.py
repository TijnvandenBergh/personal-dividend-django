from django.apps import AppConfig


class DividendsConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "dividends"

    def ready(self) -> None:  # pragma: no cover
        from django.db.models.signals import post_migrate
        from . import signals  # noqa: F401
