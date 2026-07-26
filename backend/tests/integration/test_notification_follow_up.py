import pytest
from django.utils import timezone

from apps.notifications.models import Notification
from apps.notifications.outcome_services import create_follow_up_notification
from apps.notifications.tasks import process_actionable_notification_followups
from tests.factories.accounts import VerifiedUserFactory

pytestmark = pytest.mark.django_db


def test_repeated_event_creates_one_active_follow_up():
    recipient = VerifiedUserFactory()
    arguments = {
        "recipient": recipient,
        "dedupe_key": "report:1:review",
        "event_type": Notification.EventType.PENDING_REVIEW,
        "target_type": "WeeklyProgressReport",
        "target_id": "1",
        "subject": "Review report",
        "delivery_policy": Notification.DeliveryPolicy.IN_APP,
    }
    first, first_created = create_follow_up_notification(**arguments)
    second, second_created = create_follow_up_notification(**arguments)
    assert first_created is True
    assert second_created is False
    assert first.pk == second.pk


def test_repeated_followup_job_deduplicates_reminder_and_escalation(settings):
    recipient = VerifiedUserFactory()
    now = timezone.now()
    notification, _ = create_follow_up_notification(
        recipient=recipient,
        dedupe_key="task:2:overdue",
        event_type=Notification.EventType.APPROACHING_DEADLINE,
        target_type="Task",
        target_id="2",
        subject="Task overdue",
        delivery_policy=Notification.DeliveryPolicy.IN_APP,
        due_at=now - timezone.timedelta(days=2),
    )

    assert process_actionable_notification_followups() == 2
    assert process_actionable_notification_followups() == 0
    notification.refresh_from_db()
    assert notification.reminder_count == 1
    assert notification.escalation_level == 1
