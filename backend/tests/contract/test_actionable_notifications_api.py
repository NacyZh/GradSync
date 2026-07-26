import pytest
from django.utils import timezone

from apps.notifications.models import Notification
from apps.notifications.services import enqueue_notification
from tests.factories.accounts import VerifiedUserFactory
from tests.factories.research_execution import execution_project
from tests.helpers import authenticate

pytestmark = pytest.mark.django_db


def test_notification_filters_selected_read_and_acknowledge(api_client):
    user = VerifiedUserFactory()
    notification = enqueue_notification(
        recipient=user,
        event_type=Notification.EventType.PENDING_REVIEW,
        target_type="WeeklyProgressReport",
        target_id="1",
        subject="Acknowledge review",
        category=Notification.Category.REPORT,
        requirement_type=Notification.RequirementType.ACKNOWLEDGEMENT,
        active_follow_up=True,
    )
    client = authenticate(api_client, user)
    listed = client.get("/api/notifications", {"outcome": "pending", "pageSize": 10})
    assert listed.status_code == 200
    assert listed.json()["pendingActionCount"] == 1
    read = client.post(
        "/api/notifications/read", {"notificationIds": [notification.id]}, format="json"
    )
    assert read.json()["updatedIds"] == [notification.id]
    acknowledged = client.post(f"/api/notifications/{notification.id}/acknowledge")
    assert acknowledged.status_code == 200
    assert acknowledged.json()["outcomeState"] == "acknowledged"


def test_preferences_and_project_policy_contract(api_client):
    project, advisor = execution_project()
    client = authenticate(api_client, advisor)
    preferences = client.get("/api/notification-preferences")
    assert preferences.status_code == 200
    assert preferences.json()["categories"]
    policy = client.get(f"/api/projects/{project.id}/notification-policy")
    assert policy.status_code == 200
    assert policy.json()["capabilities"]["canEdit"] is True


def test_administrator_notification_summary_contains_counts_only(api_client):
    administrator = VerifiedUserFactory(
        global_role="admin", active_role="administrator"
    )
    now = timezone.now()
    response = authenticate(api_client, administrator).get(
        "/api/admin/notifications/summary",
        {
            "from": (now - timezone.timedelta(days=1)).isoformat(),
            "to": now.isoformat(),
        },
    )
    assert response.status_code == 200
    payload = response.json()
    assert set(payload) == {
        "notifications",
        "pendingFollowUps",
        "outcomes",
        "deliveryAttempts",
    }
    assert "recipient" not in str(payload).lower()
