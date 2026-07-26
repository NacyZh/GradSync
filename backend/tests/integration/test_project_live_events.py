import pytest
from django.utils import timezone

from apps.audit.services import record_event, record_execution_event
from apps.notifications.models import Notification
from apps.projects.models import ProjectMembership, ResearchProject
from apps.submissions.models import InlineComment
from tests.factories.accounts import UserFactory
from tests.helpers import authenticate


@pytest.mark.django_db
def test_project_event_feed_orders_bounds_and_combines_sources(api_client):
    advisor = UserFactory(global_role="advisor", status="active")
    project = ResearchProject.objects.create(title="Live Events", advisor=advisor)
    ProjectMembership.objects.create(project=project, user=advisor, role="advisor")
    first = record_event(project, advisor, "project.created", "Created project", project)
    Notification.objects.create(
        project=project,
        recipient=advisor,
        sender=advisor,
        event_type=Notification.EventType.MEMBERSHIP_CHANGED,
        target_type="ProjectMembership",
        target_id="1",
        subject="Membership changed",
        eligible_at=timezone.now(),
    )
    InlineComment.objects.create(
        project=project,
        target_type=InlineComment.TargetType.PROGRESS_REPORT,
        target_id=1,
        author=advisor,
        anchor="summary",
        body="Looks good",
    )

    response = authenticate(api_client, advisor).get(
        f"/api/projects/{project.id}/events/",
        {"since": f"audit:{first.id}", "limit": "10"},
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["generatedAt"]
    assert payload["latestEventId"] == payload["results"][0]["id"]
    assert {event["source"] for event in payload["results"]} == {"notification", "comment"}
    assert all(event["id"] != f"audit:{first.id}" for event in payload["results"])


@pytest.mark.django_db
def test_project_event_feed_authorization_does_not_leak_events(api_client):
    advisor = UserFactory(global_role="advisor", status="active")
    outsider = UserFactory(global_role="student", status="active")
    project = ResearchProject.objects.create(title="Private Events", advisor=advisor)
    ProjectMembership.objects.create(project=project, user=advisor, role="advisor")
    record_event(project, advisor, "project.updated", "Private update", project)

    response = authenticate(api_client, outsider).get(f"/api/projects/{project.id}/events/")

    assert response.status_code == 404


@pytest.mark.django_db
def test_execution_event_uses_typed_target_and_stable_cursor(api_client):
    advisor = UserFactory(global_role="advisor", status="active")
    project = ResearchProject.objects.create(title="Execution Events", advisor=advisor)
    ProjectMembership.objects.create(project=project, user=advisor, role="advisor")
    event = record_execution_event(
        project=project,
        actor=advisor,
        action="notification_policy.updated",
        target=project,
        state={"version": 2},
        privileged=True,
    )

    response = authenticate(api_client, advisor).get(
        f"/api/projects/{project.id}/events/", {"limit": 500}
    )

    assert response.status_code == 200
    payload = response.json()["results"]
    assert payload[0]["id"] == f"audit:{event.id}"
    assert payload[0]["targetType"] == "ResearchProject"
    assert len(payload) <= 100
