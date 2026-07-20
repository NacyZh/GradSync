import pytest
from django.core import mail
from django.utils import timezone

from apps.notifications.tasks import deliver_due_notifications
from apps.projects.models import ProjectMembership
from apps.schedules.models import ScheduleReminder
from apps.schedules.reminder_services import create_due_schedule_reminders
from apps.schedules.services import create_schedule
from tests.factories.accounts import UserFactory
from tests.factories.shared_workspace import project_with_members

pytestmark = pytest.mark.django_db


def make_due_group_reminder():
    advisor = UserFactory(global_role="advisor")
    student = UserFactory()
    project = project_with_members(advisor=advisor, students=[student])
    now = timezone.now().replace(second=0, microsecond=0)
    item = create_schedule(
        actor=advisor,
        data={
            "scope": "group",
            "category": "meeting",
            "title": "Reminder integration",
            "all_day": False,
            "starts_at": now + timezone.timedelta(minutes=30),
            "ends_at": now + timezone.timedelta(minutes=60),
            "timezone": "UTC",
            "recurrence": {"frequency": "none", "interval": 1, "weekdays": []},
            "reminders": [],
            "audience": {"project_ids": [project.id], "account_ids": []},
        },
    )
    ScheduleReminder.objects.create(schedule_item=item, offset_minutes=30)
    return item, project, student, now


def test_schedule_reminder_email_delivery_is_idempotent():
    item, _, _, now = make_due_group_reminder()
    assert create_due_schedule_reminders(now=now) == 1
    assert create_due_schedule_reminders(now=now) == 0
    assert deliver_due_notifications() == 1
    assert deliver_due_notifications() == 0
    assert len(mail.outbox) == 1
    assert item.notification_dispatches.get(channel="email").status == "created"


def test_removed_recipient_is_skipped_before_due_scan():
    item, project, student, now = make_due_group_reminder()
    membership = ProjectMembership.objects.get(project=project, user=student, status="active")
    membership.status = ProjectMembership.Status.REMOVED
    membership.removed_at = now
    membership.save()
    assert create_due_schedule_reminders(now=now) == 0
    assert not item.notification_dispatches.filter(event_type="reminder").exists()


def test_failed_schedule_email_is_retried_without_duplicate_notification(monkeypatch):
    item, _, _, now = make_due_group_reminder()
    create_due_schedule_reminders(now=now)

    def fail_mail(*args, **kwargs):
        raise ConnectionError("temporary provider failure")

    monkeypatch.setattr("apps.notifications.tasks.send_mail", fail_mail)
    assert deliver_due_notifications() == 0
    notification = item.notification_dispatches.get(channel="email").notification
    notification.eligible_at = now
    notification.save(update_fields=["eligible_at"])
    monkeypatch.setattr("apps.notifications.tasks.send_mail", lambda *args, **kwargs: 1)
    assert deliver_due_notifications() == 1
    assert item.notification_dispatches.filter(channel="in_app", event_type="reminder").count() == 1
    assert item.notification_dispatches.get(channel="email").status == "created"
