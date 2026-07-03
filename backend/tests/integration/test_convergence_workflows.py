import pytest
from django.core import mail
from django.utils import timezone

from apps.notifications.models import Notification
from apps.notifications.tasks import (
    create_deadline_reminders,
    create_pending_review_reminders,
    deliver_due_notifications,
)
from apps.projects.models import ProjectMembership, ResearchProject
from apps.resources.models import ResourceItem, ResourceType
from apps.resources.services import BookingService
from apps.submissions.comment_services import InlineCommentService
from apps.submissions.draft_services import DraftService
from apps.submissions.models import DraftVersion, InlineComment
from apps.submissions.report_services import WeeklyReportService
from apps.tasks.models import Task
from tests.factories.accounts import UserFactory
from tests.helpers import authenticate


@pytest.mark.django_db
def test_advisor_archives_reopens_and_blocks_archived_writes(api_client):
    advisor = UserFactory(global_role="advisor")
    student = UserFactory(global_role="student")
    project = ResearchProject.objects.create(title="Archive Me", advisor=advisor)
    ProjectMembership.objects.create(project=project, user=advisor, role="advisor")
    ProjectMembership.objects.create(project=project, user=student, role="student")

    archive_response = authenticate(api_client, advisor).post(
        f"/api/projects/{project.id}/archive/"
    )
    assert archive_response.status_code == 200

    blocked = api_client.post(
        f"/api/projects/{project.id}/tasks/", {"title": "Blocked"}, format="json"
    )
    assert blocked.status_code == 403

    reopen_response = api_client.post(f"/api/projects/{project.id}/reopen/")
    assert reopen_response.status_code == 200
    allowed = api_client.post(
        f"/api/projects/{project.id}/tasks/", {"title": "Allowed"}, format="json"
    )
    assert allowed.status_code == 201


@pytest.mark.django_db
def test_task_status_change_writes_audit_and_student_cannot_change_planning_fields(api_client):
    advisor = UserFactory(global_role="advisor")
    student = UserFactory(global_role="student")
    project = ResearchProject.objects.create(title="Tasks", advisor=advisor)
    ProjectMembership.objects.create(project=project, user=advisor, role="advisor")
    ProjectMembership.objects.create(project=project, user=student, role="student")
    task = Task.objects.create(
        project=project, title="Assigned", assignee=student, created_by=advisor
    )

    response = authenticate(api_client, student).patch(
        f"/api/projects/{project.id}/tasks/{task.id}/",
        {"status": "in_progress"},
        format="json",
    )
    assert response.status_code == 200
    assert project.audit_events.filter(event_type="task.status_changed", actor=student).exists()

    denied = api_client.patch(
        f"/api/projects/{project.id}/tasks/{task.id}/", {"title": "Nope"}, format="json"
    )
    assert denied.status_code == 403


@pytest.mark.django_db
def test_review_status_comments_booking_cancel_and_notification_delivery(api_client, settings):
    settings.EMAIL_BACKEND = "django.core.mail.backends.locmem.EmailBackend"
    advisor = UserFactory(global_role="advisor", email="advisor@example.com")
    student = UserFactory(global_role="student", email="student@example.com")
    project = ResearchProject.objects.create(title="Reviews", advisor=advisor)
    ProjectMembership.objects.create(project=project, user=advisor, role="advisor")
    ProjectMembership.objects.create(project=project, user=student, role="student")

    draft = DraftService(student, project).create_draft(title="Paper")
    version = DraftService(student, project).submit_version(
        draft=draft, content_reference="paper-v1"
    )
    review_response = authenticate(api_client, advisor).patch(
        f"/api/projects/{project.id}/drafts/{draft.id}/versions/{version.id}/review/",
        {"review_status": "needs_revision"},
        format="json",
    )
    assert review_response.status_code == 200

    comment_response = api_client.post(
        f"/api/projects/{project.id}/comments/",
        {
            "target_type": "draft_version",
            "target_id": version.id,
            "anchor": "p1",
            "body": "Clarify",
        },
        format="json",
    )
    assert comment_response.status_code == 201
    comment = InlineComment.objects.get(pk=comment_response.json()["id"])
    resolved = api_client.patch(
        f"/api/projects/{project.id}/comments/{comment.id}/status/",
        {"status": "resolved"},
        format="json",
    )
    assert resolved.status_code == 200

    resource = ResourceItem.objects.create(resource_type=ResourceType.objects.create(name="seat", field_schema=[]), name="Seat")
    booking = BookingService(student, project).create_booking(
        resource_item=resource,
        starts_at=timezone.now() + timezone.timedelta(days=1),
        ends_at=timezone.now() + timezone.timedelta(days=1, hours=1),
    )
    cancel_response = authenticate(api_client, student).post(
        f"/api/projects/{project.id}/bookings/{booking.id}/cancel/"
    )
    assert cancel_response.status_code == 200
    assert cancel_response.json()["status"] == "cancelled"

    Notification.objects.create(
        project=project,
        recipient=advisor,
        sender=student,
        event_type=Notification.EventType.NEW_SUBMISSION,
        target_type="DraftVersion",
        target_id=str(version.id),
        subject="New draft",
        action_path=f"/projects/{project.id}/drafts/{draft.id}",
        eligible_at=timezone.now(),
    )
    assert deliver_due_notifications() >= 1
    assert len(mail.outbox) >= 1


@pytest.mark.django_db
def test_notification_delivery_skips_recipient_after_membership_removal(settings):
    settings.EMAIL_BACKEND = "django.core.mail.backends.locmem.EmailBackend"
    advisor = UserFactory(global_role="advisor", email="advisor-skip@example.com")
    student = UserFactory(global_role="student", email="student-skip@example.com")
    project = ResearchProject.objects.create(title="Delivery Scope", advisor=advisor)
    ProjectMembership.objects.create(project=project, user=advisor, role="advisor")
    membership = ProjectMembership.objects.create(project=project, user=student, role="student")
    notification = Notification.objects.create(
        project=project,
        recipient=student,
        sender=advisor,
        event_type=Notification.EventType.BOOKING_CHANGED,
        target_type="Booking",
        target_id="1",
        subject="Booking changed",
        action_path=f"/projects/{project.id}/resources",
        eligible_at=timezone.now(),
    )

    membership.status = "removed"
    membership.save(update_fields=["status"])

    assert deliver_due_notifications() == 0
    notification.refresh_from_db()
    assert notification.status == Notification.Status.SKIPPED
    assert "no longer an active project member" in notification.failure_reason
    assert len(mail.outbox) == 0


@pytest.mark.django_db
def test_dashboard_notifications_and_reminder_jobs_are_project_scoped(api_client):
    advisor = UserFactory(global_role="advisor")
    student = UserFactory(global_role="student")
    project = ResearchProject.objects.create(title="Dashboard", advisor=advisor)
    ProjectMembership.objects.create(project=project, user=advisor, role="advisor")
    ProjectMembership.objects.create(project=project, user=student, role="student")
    task = Task.objects.create(
        project=project,
        title="Soon",
        assignee=student,
        deadline_at=timezone.now() + timezone.timedelta(days=1),
        created_by=advisor,
    )
    version = DraftVersion.objects.create(
        project=project,
        draft=DraftService(student, project).create_draft(title="Dash Paper"),
        submitted_by=student,
        version_number=1,
        content_reference="paper",
    )
    DraftVersion.objects.filter(pk=version.pk).update(
        submitted_at=timezone.now() - timezone.timedelta(days=4)
    )
    version.refresh_from_db()

    assert create_deadline_reminders() >= 1
    assert create_pending_review_reminders() >= 1

    dashboard = authenticate(api_client, advisor).get(f"/api/projects/{project.id}/")
    assert dashboard.status_code == 200
    assert dashboard.json()["pending_reviews"]

    notifications = api_client.get(f"/api/projects/{project.id}/notifications/")
    assert notifications.status_code == 200
    assert notifications.json()["results"]
    assert project.notifications.filter(target_id=f"{task.id}:1d").exists()
    assert project.notifications.filter(target_id=str(version.id)).exists()


@pytest.mark.django_db
def test_project_scoped_search_filters_and_resource_availability(api_client):
    advisor = UserFactory(global_role="advisor")
    student = UserFactory(global_role="student")
    project = ResearchProject.objects.create(title="Searchable", advisor=advisor)
    ProjectMembership.objects.create(project=project, user=advisor, role="advisor")
    ProjectMembership.objects.create(project=project, user=student, role="student")
    other_project = ResearchProject.objects.create(title="Other", advisor=advisor)
    ProjectMembership.objects.create(project=other_project, user=advisor, role="advisor")
    ProjectMembership.objects.create(project=other_project, user=student, role="student")

    Task.objects.create(
        project=project,
        title="Analyze cells",
        priority="high",
        assignee=student,
        created_by=advisor,
    )
    Task.objects.create(
        project=project,
        title="Write appendix",
        priority="low",
        assignee=student,
        created_by=advisor,
    )
    DraftService(student, project).create_draft(title="Cell migration manuscript")
    DraftService(student, project).create_draft(title="Unrelated notes")
    report = WeeklyReportService(student, project).submit_report(
        report_week_start=timezone.localdate(),
        completed_work="Finished microscopy search target",
        blockers="",
        next_steps="Quantify results",
    )
    InlineCommentService(advisor, project).create_comment(
        target_type="progress_report",
        target_id=report.id,
        anchor="microscopy",
        body="Add quantified search target",
    )
    microscope_type = ResourceType.objects.create(
        name="Microscope",
        field_schema=[{"key": "room", "label": "Room", "fieldType": "text", "required": False}],
    )
    resource = ResourceItem.objects.create(
        resource_type=microscope_type,
        name="Confocal microscope",
        location="Room 2",
        field_values={"room": "Room 2"},
    )
    bench_type = ResourceType.objects.create(name="Bench", field_schema=[])
    open_resource = ResourceItem.objects.create(
        resource_type=bench_type, name="Open bench", location="Room 3"
    )
    BookingService(student, project).create_booking(
        resource_item=resource,
        starts_at=timezone.now() + timezone.timedelta(days=2),
        ends_at=timezone.now() + timezone.timedelta(days=2, hours=1),
        purpose="Microscopy search target",
    )

    authenticate(api_client, advisor)

    tasks = api_client.get(f"/api/projects/{project.id}/tasks/?search=cells&priority=high")
    drafts = api_client.get(f"/api/projects/{project.id}/drafts/?search=migration")
    reports = api_client.get(
        f"/api/projects/{project.id}/reports/?search=microscopy&review_status=pending_review"
    )
    comments = api_client.get(f"/api/projects/{project.id}/comments/?search=quantified&status=open")
    bookings = api_client.get(
        f"/api/projects/{project.id}/bookings/?search=microscopy&status=reserved&resourceItemId={resource.id}"
    )
    availability = api_client.get(
        "/api/resource-items/availability/",
        {
            "starts_at": (timezone.now() + timezone.timedelta(days=2, minutes=5)).isoformat(),
            "ends_at": (timezone.now() + timezone.timedelta(days=2, minutes=55)).isoformat(),
        },
    )

    assert tasks.status_code == 200
    assert [item["title"] for item in tasks.json()["results"]] == ["Analyze cells"]
    assert drafts.status_code == 200
    assert [item["title"] for item in drafts.json()["results"]] == ["Cell migration manuscript"]
    assert reports.status_code == 200
    assert len(reports.json()["results"]) == 1
    assert comments.status_code == 200
    assert len(comments.json()["results"]) == 1
    assert bookings.status_code == 200
    assert len(bookings.json()["results"]) == 1
    assert availability.status_code == 200
    availability_by_id = {item["id"]: item for item in availability.json()}
    assert availability_by_id[resource.id]["available"] is False
    assert availability_by_id[resource.id]["conflictingBookingCount"] == 1
    assert availability_by_id[open_resource.id]["available"] is True


@pytest.mark.django_db
def test_dashboard_activity_includes_comments_and_notification_delivery_events(api_client):
    advisor = UserFactory(global_role="advisor")
    student = UserFactory(global_role="student")
    project = ResearchProject.objects.create(title="Activity", advisor=advisor)
    ProjectMembership.objects.create(project=project, user=advisor, role="advisor")
    ProjectMembership.objects.create(project=project, user=student, role="student")
    report = WeeklyReportService(student, project).submit_report(
        report_week_start=timezone.localdate(),
        completed_work="Activity",
        blockers="",
        next_steps="More activity",
    )
    InlineCommentService(advisor, project).create_comment(
        target_type="progress_report", target_id=report.id, anchor="summary", body="Add detail"
    )
    Notification.objects.create(
        project=project,
        recipient=student,
        sender=advisor,
        event_type=Notification.EventType.PENDING_REVIEW,
        target_type="WeeklyProgressReport",
        target_id="1",
        subject="Pending review reminder",
        status=Notification.Status.QUEUED,
        eligible_at=timezone.now(),
    )

    response = authenticate(api_client, advisor).get(f"/api/projects/{project.id}/")

    assert response.status_code == 200
    activity = response.json()["activity"]
    assert any(item["source"] == "comment" and "summary" in item["summary"] for item in activity)
    assert any(
        item["source"] == "notification" and item["summary"] == "Pending review reminder"
        for item in activity
    )
