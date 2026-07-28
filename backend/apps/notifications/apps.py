from django.apps import AppConfig


class NotificationsConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "apps.notifications"

    def ready(self):
        from .outcome_services import register_execution_outcome_resolvers

        register_execution_outcome_resolvers()
