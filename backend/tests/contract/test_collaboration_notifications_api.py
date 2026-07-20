import pytest
from django.utils import timezone

from apps.notifications.models import Notification
from apps.notifications.services import enqueue_notification
from apps.projects.models import ProjectMembership, ResearchProject
from tests.factories.accounts import UserFactory
from tests.factories.schedules import ScheduleItemFactory
from tests.helpers import authenticate


@pytest.mark.django_db
def test_notification_status_list_contract(api_client):
    teacher = UserFactory(global_role="advisor", status="active")
    student = UserFactory(global_role="student", status="active")
    outsider = UserFactory(global_role="student", status="active")
    project = ResearchProject.objects.create(title="Notification Contract", advisor=teacher)
    ProjectMembership.objects.create(project=project, user=teacher, role="advisor")
    ProjectMembership.objects.create(project=project, user=student, role="student")

    global_notification = enqueue_notification(
        recipient=student,
        event_type=Notification.EventType.ROLE_ACTIVATION,
        target_type="RoleActivationRequest",
        target_id="42",
        subject="Role activation approved",
        action_path="/profile",
        status=Notification.Status.SENT,
    )
    global_notification.sent_at = timezone.now()
    global_notification.save(update_fields=["sent_at"])
    project_notification = enqueue_notification(
        project=project,
        recipient=student,
        sender=teacher,
        event_type=Notification.EventType.TEACHER_FEEDBACK_AVAILABLE,
        target_type="TeacherFeedback",
        target_id="8",
        subject="Feedback available",
        action_path=f"/projects/{project.id}/writing",
        status=Notification.Status.RETRY_NEEDED,
        failure_reason="SMTP provider unavailable",
    )

    student_response = authenticate(api_client, student).get("/api/notifications")
    teacher_response = authenticate(api_client, teacher).get("/api/notifications")
    outsider_response = authenticate(api_client, outsider).get("/api/notifications")

    assert student_response.status_code == 200
    payload = student_response.json()["results"]
    statuses = {item["eventType"]: item for item in payload}
    assert statuses["role_activation"]["recipientEmail"] == student.email
    assert statuses["role_activation"]["status"] == "sent"
    assert statuses["teacher_feedback_available"]["status"] == "retry_needed"
    assert statuses["teacher_feedback_available"]["failureReason"] == "SMTP provider unavailable"
    assert statuses["teacher_feedback_available"]["relatedObjectType"] == "TeacherFeedback"
    assert teacher_response.status_code == 200
    assert project_notification.id in {item["id"] for item in teacher_response.json()["results"]}
    assert outsider_response.status_code == 200
    assert outsider_response.json()["results"] == []


@pytest.mark.django_db
def test_project_notification_status_list_filters_by_authorized_project(api_client):
    teacher = UserFactory(global_role="advisor", status="active")
    student = UserFactory(global_role="student", status="active")
    outsider = UserFactory(global_role="student", status="active")
    project = ResearchProject.objects.create(title="Project Notifications", advisor=teacher)
    ProjectMembership.objects.create(project=project, user=teacher, role="advisor")
    ProjectMembership.objects.create(project=project, user=student, role="student")
    notification = enqueue_notification(
        project=project,
        recipient=student,
        sender=teacher,
        event_type=Notification.EventType.RESOURCE_USE_DECISION,
        target_type="ResourceUseSubmission",
        target_id="12",
        subject="Resource use confirmed",
        action_path="/resources",
    )

    student_response = authenticate(api_client, student).get(
        f"/api/projects/{project.id}/notifications/"
    )
    teacher_response = authenticate(api_client, teacher).get(
        f"/api/projects/{project.id}/notifications/"
    )
    outsider_response = authenticate(api_client, outsider).get(
        f"/api/projects/{project.id}/notifications/"
    )

    assert student_response.status_code == 200
    assert student_response.json()["results"][0]["id"] == notification.id
    assert teacher_response.status_code == 200
    assert teacher_response.json()["results"][0]["id"] == notification.id
    assert outsider_response.status_code == 404


@pytest.mark.django_db
def test_schedule_notification_exposes_delivery_policy_and_safe_action_path(api_client):
    recipient = UserFactory(global_role="student", status="active")
    schedule = ScheduleItemFactory(owner=recipient, organizer=recipient)
    notification = enqueue_notification(
        recipient=recipient,
        event_type=Notification.EventType.SCHEDULE_REMINDER,
        target_type="ScheduleItem",
        target_id=str(schedule.id),
        subject="Schedule reminder",
        action_path=f"/?date=2026-07-24&item=schedule%3A{schedule.id}",
        delivery_policy=Notification.DeliveryPolicy.IN_APP_EMAIL,
    )
    response = authenticate(api_client, recipient).get("/api/notifications")
    assert response.status_code == 200
    payload = next(item for item in response.json()["results"] if item["id"] == notification.id)
    assert payload["deliveryPolicy"] == "in_app_email"
    assert payload["actionPath"].startswith("/?date=")
    assert "recipientEmail" in payload


@pytest.mark.django_db
def test_notification_read_receipts_are_viewer_scoped_and_preserve_new_notifications(api_client):
    advisor = UserFactory(global_role="advisor", status="active")
    student = UserFactory(global_role="student", status="active")
    project = ResearchProject.objects.create(title="Read receipts", advisor=advisor)
    ProjectMembership.objects.create(project=project, user=advisor, role="advisor")
    ProjectMembership.objects.create(project=project, user=student, role="student")
    first = enqueue_notification(
        project=project,
        recipient=student,
        sender=advisor,
        event_type=Notification.EventType.PENDING_REVIEW,
        target_type="WeeklyProgressReport",
        target_id="1",
        subject="First notification",
    )

    student_client = authenticate(api_client, student)
    assert student_client.get("/api/notifications").json()["results"][0]["readAt"] is None
    marked = student_client.post("/api/notifications/read", {"throughId": first.id}, format="json")
    assert marked.status_code == 200
    assert marked.json()["throughId"] == first.id
    assert student_client.get("/api/notifications").json()["results"][0]["readAt"]

    advisor_payload = authenticate(api_client, advisor).get("/api/notifications").json()["results"]
    assert advisor_payload[0]["readAt"] is None

    second = enqueue_notification(
        project=project,
        recipient=student,
        sender=advisor,
        event_type=Notification.EventType.TEACHER_FEEDBACK_AVAILABLE,
        target_type="TeacherFeedback",
        target_id="2",
        subject="New notification",
    )
    student_payload = authenticate(api_client, student).get("/api/notifications").json()["results"]
    by_id = {item["id"]: item for item in student_payload}
    assert by_id[first.id]["readAt"]
    assert by_id[second.id]["readAt"] is None
