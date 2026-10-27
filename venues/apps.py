from django.apps import AppConfig


class VenuesConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "venues"

    def ready(self):
        # Подключает регистрацию SQLite-функции UNICODE_LOWER для поиска без учёта регистра.
        from venue_service import search  # noqa: F401
