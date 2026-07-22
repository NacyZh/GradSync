import pytest
from django.utils import timezone

from apps.notifications.models import Notification
from apps.notifications.tasks import deliver_due_notifications
from tests.factories.accounts import UserFactory

pytestmark = pytest.mark.django_db


def test_schedule_in_app_notification_is_terminal_and_never_emailed():
    recipient = UserFactory()
    notification = Notification.objects.create(
        recipient=recipient,
        recipient_email=recipient.email,
        event_type=Notification.EventType.SCHEDULE_PUBLISHED,
        target_type="ScheduleItem",
        target_id="1",
        subject="Schedule published",
        eligible_at=timezone.now(),
        delivery_policy=Notification.DeliveryPolicy.IN_APP,
        status=Notification.Status.IN_APP_ONLY,
    )

    deliver_due_notifications()
    notification.refresh_from_db()
    assert notification.status == Notification.Status.IN_APP_ONLY
    assert notification.sent_at is None


def test_existing_notifications_keep_email_capable_default():
    field = Notification._meta.get_field("delivery_policy")
    assert field.default == Notification.DeliveryPolicy.IN_APP_EMAIL
    assert Notification.DeliveryPolicy.EMAIL_ONLY in dict(field.flatchoices)
