import pytest
from django.utils import timezone

from apps.notifications.models import Notification
from apps.notifications.services import enqueue_notification
from tests.factories.accounts import VerifiedUserFactory
from tests.helpers import authenticate

pytestmark = pytest.mark.django_db


def test_selected_read_never_marks_another_accounts_notification(api_client):
    first = VerifiedUserFactory()
    second = VerifiedUserFactory()
    visible = enqueue_notification(
        recipient=first,
        event_type=Notification.EventType.ROLE_ACTIVATION,
        target_type="RoleActivationRequest",
        target_id="1",
        subject="Visible",
    )
    hidden = enqueue_notification(
        recipient=second,
        event_type=Notification.EventType.ROLE_ACTIVATION,
        target_type="RoleActivationRequest",
        target_id="2",
        subject="Hidden",
    )
    response = authenticate(api_client, first).post(
        "/api/notifications/read",
        {"notificationIds": [visible.id, hidden.id]},
        format="json",
    )
    assert response.status_code == 200
    assert response.json()["updatedIds"] == [visible.id]


def test_hundred_visible_notifications_do_not_leak_other_recipient(api_client):
    recipient = VerifiedUserFactory()
    other = VerifiedUserFactory()
    now = timezone.now()
    Notification.objects.bulk_create(
        [
            Notification(
                recipient=recipient,
                recipient_email=recipient.email,
                event_type=Notification.EventType.ROLE_ACTIVATION,
                target_type="RoleActivationRequest",
                target_id=str(index),
                subject=f"Visible {index}",
                eligible_at=now,
            )
            for index in range(100)
        ]
        + [
            Notification(
                recipient=other,
                recipient_email=other.email,
                event_type=Notification.EventType.ROLE_ACTIVATION,
                target_type="RoleActivationRequest",
                target_id="hidden",
                subject="Hidden recipient metadata",
                eligible_at=now,
            )
        ]
    )

    response = authenticate(api_client, recipient).get(
        "/api/notifications", {"pageSize": 100}
    )

    assert response.status_code == 200
    assert len(response.json()["results"]) == 100
    assert "Hidden recipient metadata" not in str(response.json())
