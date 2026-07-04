import pytest
from django.utils import timezone

from apps.notifications.models import Notification
from apps.notifications.services import enqueue_notification
from apps.projects.models import ProjectMembership, ResearchProject
from tests.factories.accounts import UserFactory
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
