from datetime import timedelta

import pytest
from django.utils import timezone

from apps.schedules.models import ScheduleItem
from tests.factories.accounts import UserFactory
from tests.helpers import authenticate

pytestmark = pytest.mark.django_db


def timed_payload(**overrides):
    starts_at = timezone.now() + timedelta(days=2)
    payload = {
        "scope": "personal",
        "category": "meeting",
        "title": "Private planning block",
        "description": "Owner only",
        "allDay": False,
        "startsAt": starts_at.isoformat(),
        "endsAt": (starts_at + timedelta(hours=1)).isoformat(),
        "timezone": "UTC",
        "recurrence": {"frequency": "none", "interval": 1, "weekdays": []},
        "reminders": [{"offsetMinutes": 30}],
    }
    payload.update(overrides)
    return payload


def test_private_schedule_create_detail_update_complete_and_delete(api_client):
    owner = UserFactory()
    client = authenticate(api_client, owner)
    created = client.post("/api/schedules/", timed_payload(), format="json")
    assert created.status_code == 201, created.json()
    schedule_id = created.json()["id"]
    assert created.json()["scope"] == "personal"
    assert created.json()["capabilities"]["canDelete"] is True

    detail = client.get(f"/api/schedules/{schedule_id}/")
    assert detail.status_code == 200
    updated = client.patch(
        f"/api/schedules/{schedule_id}/",
        {
            "expectedVersion": 1,
            "changeScope": "series",
            "fields": {"title": "Protected writing block"},
        },
        format="json",
    )
    assert updated.status_code == 200
    assert updated.json()["title"] == "Protected writing block"
    assert updated.json()["version"] == 2

    completed = client.post(
        f"/api/schedules/{schedule_id}/complete/",
        {"expectedVersion": 2, "changeScope": "series", "confirmed": True},
        format="json",
    )
    assert completed.status_code == 200
    assert completed.json()["status"] == "completed"

    removed = client.delete(
        f"/api/schedules/{schedule_id}/",
        {"expectedVersion": 3, "changeScope": "series", "confirmed": True},
        format="json",
    )
    assert removed.status_code == 204
    assert not ScheduleItem.objects.filter(pk=schedule_id).exists()


def test_private_detail_is_hidden_and_stale_or_unconfirmed_writes_fail(api_client):
    owner = UserFactory()
    other = UserFactory(global_role="admin")
    created = authenticate(api_client, owner).post(
        "/api/schedules/", timed_payload(), format="json"
    )
    schedule_id = created.json()["id"]

    assert authenticate(api_client, other).get(f"/api/schedules/{schedule_id}/").status_code == 404
    stale = authenticate(api_client, owner).patch(
        f"/api/schedules/{schedule_id}/",
        {"expectedVersion": 2, "changeScope": "series", "fields": {"title": "Lost"}},
        format="json",
    )
    assert stale.status_code == 409
    assert stale.json()["code"] == "stale_schedule_version"
    unconfirmed = authenticate(api_client, owner).delete(
        f"/api/schedules/{schedule_id}/",
        {"expectedVersion": 1, "changeScope": "series", "confirmed": False},
        format="json",
    )
    assert unconfirmed.status_code == 400


def test_conflicts_are_non_blocking_and_owner_visible_only(api_client):
    owner = UserFactory()
    starts_at = timezone.now() + timedelta(days=3)
    authenticate(api_client, owner).post(
        "/api/schedules/",
        timed_payload(
            startsAt=starts_at.isoformat(), endsAt=(starts_at + timedelta(hours=2)).isoformat()
        ),
        format="json",
    )
    response = authenticate(api_client, owner).post(
        "/api/schedules/conflicts/",
        {
            "allDay": False,
            "startsAt": (starts_at + timedelta(minutes=30)).isoformat(),
            "endsAt": (starts_at + timedelta(hours=1)).isoformat(),
            "timezone": "UTC",
        },
        format="json",
    )
    assert response.status_code == 200
    assert response.json()["results"][0]["title"] == "Private planning block"

    other = UserFactory()
    hidden = authenticate(api_client, other).post(
        "/api/schedules/conflicts/",
        {
            "allDay": False,
            "startsAt": (starts_at + timedelta(minutes=30)).isoformat(),
            "endsAt": (starts_at + timedelta(hours=1)).isoformat(),
            "timezone": "UTC",
        },
        format="json",
    )
    assert hidden.json()["results"] == []


def test_staff_searches_bounded_audience_options_and_student_is_denied(api_client):
    advisor = UserFactory(global_role="advisor")
    student = UserFactory(name="Eligible Member")
    from tests.factories.shared_workspace import project_with_members

    project_with_members(advisor=advisor, students=[student], title="Carbon Group")
    response = authenticate(api_client, advisor).get(
        "/api/schedules/audience-options/", {"type": "account", "q": "Eligible"}
    )
    assert response.status_code == 200
    assert any(option["id"] == student.id for option in response.json()["results"])
    assert (
        authenticate(api_client, student)
        .get("/api/schedules/audience-options/", {"type": "account"})
        .status_code
        == 403
    )


def test_advisor_creates_group_schedule_for_selected_project(api_client):
    advisor = UserFactory(global_role="advisor")
    student = UserFactory()
    from tests.factories.shared_workspace import project_with_members

    project = project_with_members(advisor=advisor, students=[student])
    response = authenticate(api_client, advisor).post(
        "/api/schedules/",
        timed_payload(
            scope="group",
            audience={"projectIds": [project.id], "accountIds": [student.id]},
        ),
        format="json",
    )
    assert response.status_code == 201, response.json()
    assert response.json()["scope"] == "group"
    assert response.json()["audience"]["projectIds"] == [project.id]

    denied = authenticate(api_client, student).post(
        "/api/schedules/",
        timed_payload(scope="group", audience={"accountIds": [advisor.id]}),
        format="json",
    )
    assert denied.status_code == 403


def test_group_cancel_revision_and_delivery_contracts(api_client):
    advisor = UserFactory(global_role="advisor")
    student = UserFactory()
    from tests.factories.shared_workspace import project_with_members

    project = project_with_members(advisor=advisor, students=[student])
    created = authenticate(api_client, advisor).post(
        "/api/schedules/",
        timed_payload(scope="group", audience={"projectIds": [project.id]}),
        format="json",
    )
    schedule_id = created.json()["id"]
    cancelled = authenticate(api_client, advisor).post(
        f"/api/schedules/{schedule_id}/cancel/",
        {
            "expectedVersion": 1,
            "changeScope": "series",
            "confirmed": True,
            "reason": "No longer required",
        },
        format="json",
    )
    assert cancelled.status_code == 200, cancelled.json()
    assert cancelled.json()["status"] == "cancelled"
    revisions = authenticate(api_client, student).get(f"/api/schedules/{schedule_id}/revisions/")
    assert revisions.status_code == 200
    assert revisions.json()["results"][0]["changeType"] == "cancelled"
    delivery = authenticate(api_client, advisor).get(
        f"/api/schedules/{schedule_id}/delivery-status/"
    )
    assert delivery.status_code == 200
    assert delivery.json()["notifications"]["emailQueued"] == 1
    assert (
        authenticate(api_client, student)
        .get(f"/api/schedules/{schedule_id}/delivery-status/")
        .status_code
        == 403
    )
