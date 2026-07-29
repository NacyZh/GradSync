import pytest
from django.utils import timezone

from apps.audit.models import AuditEvent
from apps.notifications.models import Notification, NotificationDeliveryAttempt
from apps.projects.models import ProjectMembership, ResearchProject
from apps.submissions.models import ReportingPeriod, ReportTemplate, ReportTemplateVersion
from apps.tasks.models import Task
from tests.factories.accounts import UserFactory


@pytest.mark.django_db
def test_administrator_receives_cross_project_health_snapshot(api_client):
    now = timezone.now()
    admin = UserFactory(global_role="admin")
    advisor = UserFactory(global_role="advisor")
    student = UserFactory(global_role="student")
    project = ResearchProject.objects.create(
        title="Delayed imaging study",
        advisor=advisor,
        ends_on=timezone.localdate() - timezone.timedelta(days=2),
        governance_state=ResearchProject.GovernanceState.HOLD,
        governance_hold_reason=ResearchProject.GovernanceHoldReason.MANUAL_CORRECTION,
        governance_hold_started_at=now - timezone.timedelta(days=3),
    )
    ProjectMembership.objects.create(
        project=project,
        user=advisor,
        role=ProjectMembership.Role.ADVISOR,
    )
    ProjectMembership.objects.create(
        project=project,
        user=student,
        role=ProjectMembership.Role.STUDENT,
    )
    task = Task.objects.create(
        project=project,
        title="Repair image pipeline",
        status=Task.Status.BLOCKED,
        deadline_at=now - timezone.timedelta(days=1),
        created_by=advisor,
    )
    Task.objects.filter(pk=task.pk).update(updated_at=now - timezone.timedelta(days=9))

    template = ReportTemplate.objects.create(
        project=project,
        name="Weekly update",
        created_by=advisor,
    )
    version = ReportTemplateVersion.objects.create(
        project=project,
        template=template,
        version_number=1,
        status=ReportTemplateVersion.Status.PUBLISHED,
        created_by=advisor,
        published_by=advisor,
        published_at=now,
    )
    ReportingPeriod.objects.create(
        project=project,
        starts_on=timezone.localdate() - timezone.timedelta(days=7),
        ends_on=timezone.localdate() - timezone.timedelta(days=1),
        deadline_at=now - timezone.timedelta(hours=1),
        template_version=version,
        generation_key="health:test:period",
    )
    AuditEvent.objects.create(
        project=project,
        event_type="booking.capacity_conflict",
        target_type="Booking",
        target_id="1",
        summary="Capacity conflict",
    )
    notification = Notification.objects.create(
        project=project,
        recipient=advisor,
        event_type=Notification.EventType.PENDING_REVIEW,
        target_type="WeeklyProgressReport",
        target_id="1",
        subject="Review failed delivery",
        eligible_at=now,
    )
    NotificationDeliveryAttempt.objects.create(
        notification=notification,
        channel=NotificationDeliveryAttempt.Channel.EMAIL,
        state=NotificationDeliveryAttempt.State.FAILED,
        eligible_at=now,
        attempted_at=now,
        completed_at=now,
        idempotency_key="health:test:email",
    )

    api_client.force_authenticate(admin)
    response = api_client.get("/api/admin/project-health/")

    assert response.status_code == 200
    assert response.data["summary"] == {
        "activeProjects": 1,
        "overdueProjects": 1,
        "overdueProjectRate": 100.0,
        "longBlockedTasks": 1,
        "missingReports": 1,
        "governanceHolds": 1,
        "resourceConflicts": 1,
        "notificationFailures": 1,
        "notificationFailureRate": 100.0,
    }
    assert response.data["projects"][0]["healthLevel"] == "critical"
    assert response.data["projects"][0]["actionPath"] == f"/projects/{project.id}"
    assert response.data["blockedTasks"][0]["blockedDays"] >= 9
    assert response.data["missingReports"][0]["missingCount"] == 1
    assert len(response.data["trend"]) == 14
    assert sum(point["resourceConflicts"] for point in response.data["trend"]) == 1
    assert sum(point["notificationFailures"] for point in response.data["trend"]) == 1


@pytest.mark.django_db
def test_project_health_snapshot_is_administrator_only(api_client):
    advisor = UserFactory(global_role="advisor")
    api_client.force_authenticate(advisor)

    response = api_client.get("/api/admin/project-health/")

    assert response.status_code == 403
