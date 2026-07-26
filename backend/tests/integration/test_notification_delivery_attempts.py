import pytest
from django.core import mail
from django.utils import timezone

from apps.notifications.models import Notification, NotificationDeliveryAttempt
from apps.notifications.services import enqueue_notification
from apps.notifications.tasks import deliver_due_notifications
from tests.factories.accounts import VerifiedUserFactory

pytestmark = pytest.mark.django_db


def test_email_attempt_and_in_app_fallback_are_recorded():
    user = VerifiedUserFactory()
    notification = enqueue_notification(
        recipient=user,
        event_type=Notification.EventType.ROLE_ACTIVATION,
        target_type="RoleActivationRequest",
        target_id="1",
        subject="Role activated",
    )
    assert deliver_due_notifications() == 1
    assert len(mail.outbox) == 1
    states = set(notification.delivery_attempts.values_list("channel", "state"))
    assert ("in_app", NotificationDeliveryAttempt.State.SENT) in states
    assert ("email", NotificationDeliveryAttempt.State.SENT) in states


def test_email_failure_is_masked_and_does_not_remove_in_app(monkeypatch):
    user = VerifiedUserFactory()
    notification = enqueue_notification(
        recipient=user,
        event_type=Notification.EventType.ROLE_ACTIVATION,
        target_type="RoleActivationRequest",
        target_id="2",
        subject="Role activated",
    )
    monkeypatch.setattr(
        "apps.notifications.tasks.send_mail",
        lambda *args, **kwargs: (_ for _ in ()).throw(RuntimeError("token=private")),
    )
    assert deliver_due_notifications() == 0
    notification.refresh_from_db()
    assert notification.status == Notification.Status.RETRY_NEEDED
    assert "private" not in notification.failure_reason
    assert notification.delivery_attempts.filter(channel="in_app", state="sent").exists()


def test_email_retry_exhaustion_finishes_as_failed(monkeypatch):
    user = VerifiedUserFactory()
    notification = enqueue_notification(
        recipient=user,
        event_type=Notification.EventType.ROLE_ACTIVATION,
        target_type="RoleActivationRequest",
        target_id="3",
        subject="Role activated",
    )
    monkeypatch.setattr(
        "apps.notifications.tasks.send_mail",
        lambda *args, **kwargs: (_ for _ in ()).throw(ConnectionError("unavailable")),
    )
    for _ in range(5):
        notification.eligible_at = timezone.now()
        notification.save(update_fields=["eligible_at"])
        assert deliver_due_notifications() == 0
        notification.refresh_from_db()

    assert notification.status == Notification.Status.FAILED
    assert notification.retry_count == 5
    assert notification.delivery_attempts.filter(channel="email", state="failed").count() == 5
