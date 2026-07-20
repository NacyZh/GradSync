import pytest

from apps.projects.models import ResearchProject
from tests.factories.accounts import UserFactory
from tests.factories.shared_workspace import project_with_members
from tests.helpers import authenticate

pytestmark = pytest.mark.django_db


def test_unconfigured_report_schedule_is_204_for_project_member(api_client):
    student = UserFactory()
    project = project_with_members(students=[student])

    response = authenticate(api_client, student).get(f"/api/projects/{project.id}/report-schedule/")
    assert response.status_code == 204


def test_advisor_configures_updates_and_removes_report_schedule(api_client):
    advisor = UserFactory(global_role="advisor")
    project = project_with_members(advisor=advisor)
    client = authenticate(api_client, advisor)
    path = f"/api/projects/{project.id}/report-schedule/"

    created = client.put(
        path,
        {"weekday": 5, "deadlineLocalTime": "18:00", "timezone": "Asia/Shanghai"},
        format="json",
    )
    assert created.status_code == 200
    assert created.json()["version"] == 1

    stale = client.put(
        path,
        {
            "weekday": 4,
            "deadlineLocalTime": "17:00",
            "timezone": "Asia/Shanghai",
            "expectedVersion": 0,
        },
        format="json",
    )
    assert stale.status_code == 409

    removed = client.delete(path, {"expectedVersion": 1}, format="json")
    assert removed.status_code == 204


def test_student_cannot_write_and_archived_project_cannot_be_configured(api_client):
    student = UserFactory()
    project = project_with_members(students=[student])
    path = f"/api/projects/{project.id}/report-schedule/"
    payload = {"weekday": 5, "deadlineLocalTime": "18:00", "timezone": "UTC"}
    assert authenticate(api_client, student).put(path, payload, format="json").status_code == 403

    admin = UserFactory(global_role="admin")
    project.status = ResearchProject.Status.ARCHIVED
    project.save(update_fields=["status"])
    assert authenticate(api_client, admin).put(path, payload, format="json").status_code == 400
