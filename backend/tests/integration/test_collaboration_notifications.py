import pytest
from django.core.files.uploadedfile import SimpleUploadedFile

from apps.accounts.models import EmailVerificationCode
from apps.accounts.services import register_account
from apps.notifications.models import Notification
from apps.notifications.tasks import deliver_due_notifications
from apps.projects.models import ProjectMembership, ResearchProject
from apps.resources.models import ResourceItem, ResourceType, ResourceUseSubmission
from apps.resources.services import ResourceInventoryService
from apps.submissions.models import TeacherFeedback, WritingParticipant, WritingProject
from tests.factories.accounts import UserFactory
from tests.helpers import authenticate


def _docx(name="annotated.docx", body=b"notes"):
    return SimpleUploadedFile(
        name,
        body,
        content_type="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
    )


@pytest.mark.django_db
def test_email_failure_preserves_feedback_and_records_retry_needed_with_masking(
    api_client, monkeypatch
):
    teacher = UserFactory(global_role="advisor", status="active")
    student = UserFactory(global_role="student", status="active")
    project = ResearchProject.objects.create(title="Notification Failure", advisor=teacher)
    ProjectMembership.objects.create(project=project, user=teacher, role="advisor")
    ProjectMembership.objects.create(project=project, user=student, role="student")
    writing_project = WritingProject.objects.create(
        project=project,
        student=student,
        title="Chapter",
        writing_type=WritingProject.WritingType.THESIS,
    )
    WritingParticipant.objects.create(
        writing_project=writing_project,
        user=teacher,
        participant_role=WritingParticipant.Role.BOUND_ADVISOR,
    )
    version_response = authenticate(api_client, student).post(
        f"/api/writing-projects/{writing_project.id}/versions",
        {"file": _docx("chapter.docx", b"chapter")},
        format="multipart",
    )
    feedback_response = authenticate(api_client, teacher).post(
        f"/api/writing-versions/{version_response.data['id']}/feedback",
        {"annotatedFile": _docx(), "comments": "Revise methods"},
        format="multipart",
    )

    def fail_send_mail(*args, **kwargs):
        raise RuntimeError("smtp rejected token=secret verification code: 123456")

    monkeypatch.setattr("apps.notifications.tasks.send_mail", fail_send_mail)

    assert feedback_response.status_code == 201
    assert deliver_due_notifications() == 0

    feedback = TeacherFeedback.objects.get(pk=feedback_response.data["id"])
    notification = feedback.notification
    notification.refresh_from_db()
    assert feedback.comments == "Revise methods"
    assert notification.status == Notification.Status.RETRY_NEEDED
    assert notification.retry_count == 1
    assert notification.last_attempt_at is not None
    assert "secret" not in notification.failure_reason
    assert "123456" not in notification.failure_reason
    assert "[masked]" in notification.failure_reason


@pytest.mark.django_db
def test_registration_email_failure_preserves_user_and_verification_code(monkeypatch):
    def fail_send_mail(*args, **kwargs):
        raise RuntimeError("smtp password=super-secret unavailable")

    monkeypatch.setattr("apps.accounts.services.send_mail", fail_send_mail)

    user, code = register_account(
        email="notify-student@example.edu",
        password="StrongPass1!",
        nickname="Notify Student",
        requested_role="student",
        degree_type="masters",
    )

    notification = Notification.objects.get(
        recipient=user,
        event_type=Notification.EventType.VERIFICATION_CODE,
        target_id=str(code.id),
    )
    assert user.email == "notify-student@example.edu"
    assert EmailVerificationCode.objects.filter(pk=code.id, status="pending").exists()
    assert notification.status == Notification.Status.RETRY_NEEDED
    assert "super-secret" not in notification.failure_reason
    assert "[masked]" in notification.failure_reason


@pytest.mark.django_db
def test_resource_use_decision_creates_student_visible_notification():
    teacher = UserFactory(global_role="advisor", status="active")
    student = UserFactory(global_role="student", status="active")
    resource_type = ResourceType.objects.create(name="Instrument")
    resource = ResourceItem.objects.create(resource_type=resource_type, name="Spectrometer")
    submission = ResourceUseSubmission.objects.create(
        resource_item=resource,
        student=student,
        submission_type=ResourceUseSubmission.SubmissionType.REQUEST,
        details="Need access",
    )

    decided = ResourceInventoryService(teacher).decide_use_submission(
        submission,
        status=ResourceUseSubmission.Status.CONFIRMED,
        decision_note="Approved",
    )

    notification = Notification.objects.get(
        recipient=student,
        event_type=Notification.EventType.RESOURCE_USE_DECISION,
        target_id=str(decided.id),
    )
    assert decided.status == ResourceUseSubmission.Status.CONFIRMED
    assert notification.status == Notification.Status.PENDING
    assert notification.subject == "Resource use confirmed"
