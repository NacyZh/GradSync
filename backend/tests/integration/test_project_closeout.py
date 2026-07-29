import io
import json
import zipfile
from datetime import date, timedelta

import pytest
from django.utils import timezone

from apps.projects.models import ProjectCloseoutRecord, ProjectMaterial, ProjectMembership
from apps.resources.models import Booking
from apps.submissions.models import WeeklyProgressReport
from apps.tasks.models import Task
from tests.factories.accounts import VerifiedUserFactory
from tests.factories.collaboration import ProjectMembershipFactory, ResearchProjectFactory
from tests.factories.resources import BookingFactory


def closeout_payload(**overrides):
    return {
        "cancelOpenTasks": True,
        "closePendingReports": True,
        "cancelOpenBookings": True,
        "materialsReviewed": True,
        "finalPackageConfirmed": True,
        "notes": "Final records reviewed.",
        **overrides,
    }


@pytest.mark.django_db
def test_closeout_preflight_and_archive_resolve_disposable_work(api_client):
    advisor = VerifiedUserFactory(global_role="advisor", active_role="teacher")
    student = VerifiedUserFactory(name="Closeout Student")
    project = ResearchProjectFactory(advisor=advisor, title="Closeout Study")
    ProjectMembershipFactory(
        project=project,
        user=advisor,
        role=ProjectMembership.Role.ADVISOR,
    )
    ProjectMembershipFactory(project=project, user=student)
    task = Task.objects.create(
        project=project,
        title="Unfinished analysis",
        created_by=advisor,
    )
    report = WeeklyProgressReport.objects.create(
        project=project,
        student=student,
        report_week_start=date(2026, 7, 20),
        completed_work="Analysis",
        next_steps="Finish",
    )
    future_booking = BookingFactory(
        project=project,
        requested_by=student,
        starts_at=timezone.now() + timedelta(days=2),
        ends_at=timezone.now() + timedelta(days=2, hours=1),
        status=Booking.Status.CONFIRMED,
    )
    api_client.force_authenticate(advisor)

    preflight = api_client.get(f"/api/projects/{project.id}/closeout/")
    assert preflight.status_code == 200
    checks = {check["key"]: check for check in preflight.json()["checks"]}
    assert checks["incompleteTasks"]["count"] == 1
    assert checks["pendingReports"]["count"] == 1
    assert checks["openBookings"]["count"] == 1
    assert preflight.json()["ready"] is True

    response = api_client.post(
        f"/api/projects/{project.id}/archive/",
        closeout_payload(),
        format="json",
    )

    assert response.status_code == 200
    assert response.json()["status"] == "archived"
    task.refresh_from_db()
    report.refresh_from_db()
    future_booking.refresh_from_db()
    project.refresh_from_db()
    assert task.status == Task.Status.CANCELLED
    assert report.review_status == WeeklyProgressReport.ReviewStatus.CLOSED
    assert future_booking.status == Booking.Status.CANCELLED
    assert project.status == "archived"
    closeout = ProjectCloseoutRecord.objects.get(project=project)
    assert closeout.archive_version == 1
    assert all(closeout.checklist.values())


@pytest.mark.django_db
def test_closeout_rejects_pending_material_classification_and_unreturned_resource(api_client):
    advisor = VerifiedUserFactory(global_role="advisor", active_role="teacher")
    project = ResearchProjectFactory(advisor=advisor)
    ProjectMembershipFactory(project=project, user=advisor, role="advisor")
    ProjectMaterial.objects.create(
        source_project=project,
        material_type=ProjectMaterial.MaterialType.DOCUMENT,
        backing_record_id=999,
        classification_state=ProjectMaterial.ClassificationState.PENDING_REVIEW,
        created_by=advisor,
    )
    BookingFactory(
        project=project,
        starts_at=timezone.now() - timedelta(hours=2),
        ends_at=timezone.now() + timedelta(hours=1),
        status=Booking.Status.CONFIRMED,
    )
    api_client.force_authenticate(advisor)

    preflight = api_client.get(f"/api/projects/{project.id}/closeout/")
    checks = {check["key"]: check for check in preflight.json()["checks"]}
    assert preflight.json()["ready"] is False
    assert checks["pendingMaterialPermissions"]["severity"] == "blocked"
    assert checks["unreturnedResources"]["severity"] == "blocked"

    response = api_client.post(
        f"/api/projects/{project.id}/archive/",
        closeout_payload(),
        format="json",
    )
    assert response.status_code == 400
    project.refresh_from_db()
    assert project.status == "active"


@pytest.mark.django_db
def test_project_export_is_a_bounded_zip_and_students_cannot_export(api_client):
    advisor = VerifiedUserFactory(global_role="advisor", active_role="teacher")
    student = VerifiedUserFactory()
    project = ResearchProjectFactory(advisor=advisor, title="Export Study")
    ProjectMembershipFactory(project=project, user=advisor, role="advisor")
    ProjectMembershipFactory(project=project, user=student)
    Task.objects.create(project=project, title="Exported task", created_by=advisor)
    Task.objects.create(project=project, title="=unsafe formula", created_by=advisor)

    api_client.force_authenticate(student)
    closeout_forbidden = api_client.get(f"/api/projects/{project.id}/closeout/")
    forbidden = api_client.get(f"/api/projects/{project.id}/export/")
    assert closeout_forbidden.status_code == 403
    assert forbidden.status_code == 403

    api_client.force_authenticate(advisor)
    response = api_client.get(f"/api/projects/{project.id}/export/")
    assert response.status_code == 200
    assert response["Content-Type"] == "application/zip"
    payload = b"".join(response.streaming_content)
    with zipfile.ZipFile(io.BytesIO(payload)) as archive:
        assert {
            "manifest.json",
            "members.csv",
            "tasks.csv",
            "reports.csv",
            "materials.csv",
            "final-deliverables.json",
        }.issubset(archive.namelist())
        manifest = json.loads(archive.read("manifest.json"))
        assert manifest["project"]["title"] == "Export Study"
        assert b"Exported task" in archive.read("tasks.csv")
        assert b"'=unsafe formula" in archive.read("tasks.csv")
