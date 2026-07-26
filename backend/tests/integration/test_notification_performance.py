from time import monotonic

import pytest
from django.utils import timezone

from apps.notifications.models import Notification
from tests.factories.accounts import VerifiedUserFactory
from tests.helpers import authenticate

pytestmark = pytest.mark.django_db


def test_one_thousand_notifications_remain_bounded(
    api_client, django_assert_max_num_queries
):
    recipient = VerifiedUserFactory()
    Notification.objects.bulk_create(
        [
            Notification(
                recipient=recipient,
                recipient_email=recipient.email,
                event_type=Notification.EventType.APPROACHING_DEADLINE,
                target_type="Task",
                target_id=str(index),
                subject=f"Bounded notification {index}",
                eligible_at=timezone.now(),
                category=Notification.Category.PROJECT,
            )
            for index in range(1000)
        ]
    )
    started = monotonic()
    with django_assert_max_num_queries(8):
        response = authenticate(api_client, recipient).get(
            "/api/notifications", {"pageSize": 100}
        )
    elapsed = monotonic() - started

    assert response.status_code == 200
    assert len(response.json()["results"]) == 100
    assert response.json()["nextCursor"]
    assert elapsed < 3
