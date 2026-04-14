from django.apps import AppConfig


class DividendsConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "dividends"

    def ready(self) -> None:  # pragma: no cover
        from . import signals  # noqa: F401 pylint: disable=import-outside-toplevel,unused-import
