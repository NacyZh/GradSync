from datetime import timedelta

import pytest
from django.utils import timezone

from apps.resources.models import Booking
from apps.submissions.models import WeeklyProgressReport
from apps.tasks.models import Task
from tests.factories.accounts import UserFactory
from tests.factories.resources import ResourceItemFactory
from tests.factories.schedules import ProjectReportScheduleFactory
from tests.factories.shared_workspace import project_with_members
from tests.helpers import authenticate

pytestmark = pytest.mark.django_db


def test_calendar_projects_authorized_sources_and_excludes_unrelated_records(api_client):
    now = timezone.now()
    student = UserFactory()
    other = UserFactory()
    project = project_with_members(students=[student])
    hidden_project = project_with_members(students=[other], title="Hidden project")
    project.starts_on = now.date() + timedelta(days=1)
    project.ends_on = now.date() + timedelta(days=20)
    project.save()
    task = Task.objects.create(
        project=project,
        title="Assigned deadline",
        created_by=project.advisor,
        deadline_at=now + timedelta(days=2),
    )
    task.assignees.add(student)
    Task.objects.create(
        project=hidden_project,
        title="Secret deadline",
        created_by=hidden_project.advisor,
        deadline_at=now + timedelta(days=2),
    )
    WeeklyProgressReport.objects.create(
        project=project,
        student=student,
        report_week_start=now.date(),
        completed_work="Done",
        next_steps="Continue",
    )
    ProjectReportScheduleFactory(project=project, updated_by=project.advisor, weekday=5)
    Booking.objects.create(
        project=project,
        resource_item=ResourceItemFactory(),
        requested_by=student,
        starts_at=now + timedelta(days=3),
        ends_at=now + timedelta(days=3, hours=1),
    )

    response = authenticate(api_client, student).get(
        "/api/calendar/occurrences/",
        {"startsAt": now.isoformat(), "endsAt": (now + timedelta(days=31)).isoformat()},
    )

    assert response.status_code == 200
    results = response.json()["results"]
    assert {item["sourceType"] for item in results} >= {"project", "task", "report", "booking"}
    assert "Secret deadline" not in {item["title"] for item in results}
    assert any(item["sourceType"] == "report" and item["status"] == "pending" for item in results)


def test_unconfigured_or_archived_project_has_no_future_report_deadline(api_client):
    now = timezone.now()
    student = UserFactory()
    project = project_with_members(students=[student])
    project.status = "archived"
    project.save(update_fields=["status"])
    WeeklyProgressReport.objects.create(
        project=project,
        student=student,
        report_week_start=now.date(),
        completed_work="Historical work",
        next_steps="Historical next step",
    )

    response = authenticate(api_client, student).get(
        "/api/calendar/occurrences/",
        {"startsAt": now.isoformat(), "endsAt": (now + timedelta(days=30)).isoformat()},
    )

    report_items = [item for item in response.json()["results"] if item["sourceType"] == "report"]
    assert len(report_items) == 1
    assert report_items[0]["status"] == "completed"
