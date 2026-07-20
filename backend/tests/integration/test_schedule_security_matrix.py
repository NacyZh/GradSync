import pytest
from django.utils import timezone

from apps.notifications.models import Notification
from apps.notifications.services import enqueue_notification
from apps.schedules.services import create_schedule
from tests.factories.accounts import UserFactory
from tests.factories.shared_workspace import project_with_members
from tests.helpers import authenticate

pytestmark = pytest.mark.django_db


def private_item(owner, title="<script>private()</script>"):
    starts_at = timezone.now() + timezone.timedelta(days=1)
    return create_schedule(
        actor=owner,
        data={
            "scope": "personal",
            "category": "personal",
            "title": title,
            "description": "<img src=x onerror=private()>",
            "all_day": False,
            "starts_at": starts_at,
            "ends_at": starts_at + timezone.timedelta(hours=1),
            "timezone": "UTC",
            "recurrence": {"frequency": "none", "interval": 1, "weekdays": []},
            "reminders": [],
        },
    )


@pytest.mark.parametrize("role", ["student", "advisor", "admin"])
def test_private_schedule_is_owner_only_across_direct_and_projection_paths(api_client, role):
    owner = UserFactory(global_role="student")
    outsider = UserFactory(global_role=role)
    item = private_item(owner)
    client = authenticate(api_client, outsider)
    assert client.get(f"/api/schedules/{item.id}/").status_code == 404
    period = client.get(
        "/api/calendar/occurrences/",
        {
            "startsAt": (item.starts_at - timezone.timedelta(hours=1)).isoformat(),
            "endsAt": (item.ends_at + timezone.timedelta(hours=1)).isoformat(),
            "sources": "schedule",
        },
    )
    assert item.title not in str(period.json())
    assert client.get("/api/calendar/events/").json()["results"] == []
    conflict = client.post(
        "/api/schedules/conflicts/",
        {
            "allDay": False,
            "startsAt": item.starts_at.isoformat(),
            "endsAt": item.ends_at.isoformat(),
            "timezone": "UTC",
        },
        format="json",
    )
    assert item.title not in str(conflict.json())


def test_forged_schedule_notification_target_is_filtered(api_client):
    owner = UserFactory()
    outsider = UserFactory()
    item = private_item(owner, title="Sensitive plan")
    enqueue_notification(
        recipient=outsider,
        event_type=Notification.EventType.SCHEDULE_REMINDER,
        target_type="ScheduleItem",
        target_id=str(item.id),
        subject="Generic reminder",
        action_path=f"/?item=schedule%3A{item.id}",
    )
    response = authenticate(api_client, outsider).get("/api/notifications")
    assert response.status_code == 200
    assert response.json()["results"] == []


def test_group_recipient_can_read_revisions_but_not_delivery_or_audience_options(api_client):
    advisor = UserFactory(global_role="advisor")
    student = UserFactory(global_role="student")
    outsider = UserFactory(global_role="student")
    project = project_with_members(advisor=advisor, students=[student])
    starts_at = timezone.now() + timezone.timedelta(days=1)
    item = create_schedule(
        actor=advisor,
        data={
            "scope": "group",
            "category": "meeting",
            "title": "Visible group meeting",
            "all_day": False,
            "starts_at": starts_at,
            "ends_at": starts_at + timezone.timedelta(hours=1),
            "timezone": "UTC",
            "recurrence": {"frequency": "none", "interval": 1, "weekdays": []},
            "reminders": [],
            "audience": {"project_ids": [project.id], "account_ids": []},
        },
    )
    recipient = authenticate(api_client, student)
    assert recipient.get(f"/api/schedules/{item.id}/revisions/").status_code == 200
    assert recipient.get(f"/api/schedules/{item.id}/delivery-status/").status_code == 403
    assert recipient.get("/api/schedules/audience-options/?type=account").status_code == 403
    assert authenticate(api_client, outsider).get(f"/api/schedules/{item.id}/").status_code == 404
