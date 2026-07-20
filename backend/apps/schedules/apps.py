from django.apps import AppConfig


class SchedulesConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "apps.schedules"

    def ready(self):
        from . import signals  # noqa: F401
