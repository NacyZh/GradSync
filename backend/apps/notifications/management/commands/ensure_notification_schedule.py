from django.core.management.base import BaseCommand

from apps.notifications.tasks import ensure_periodic_notification_tasks


class Command(BaseCommand):
    help = (
        "Create or update Celery Beat schedules for GradSync notification reminders and delivery."
    )

    def handle(self, *args, **options):
        created = ensure_periodic_notification_tasks()
        self.stdout.write(self.style.SUCCESS(f"Notification schedules ready ({created} created)"))
