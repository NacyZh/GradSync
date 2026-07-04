import pytest
from django.core.files.uploadedfile import SimpleUploadedFile
from django.utils import timezone

from apps.audit.models import AuditEvent
from apps.library.models import DocumentCategory, DocumentRecord, PaperRecord
from apps.notifications.models import Notification
from apps.projects.models import ProjectMembership, ResearchProject
from apps.resources.models import ResourceItem, ResourceType, ResourceUseSubmission
from apps.submissions.models import TeacherFeedback, WritingProject, WritingVersion
from tests.factories.accounts import UserFactory
from tests.factories.collaboration import UploadedFileFactory
from tests.helpers import authenticate


def _docx(name="annotated.docx", body=b"notes"):
    return SimpleUploadedFile(
        name,
        body,
        content_type="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
    )


@pytest.mark.django_db
def test_role_activation_and_project_membership_are_privileged(api_client):
    admin = UserFactory(global_role="admin", status="active")
    teacher = UserFactory(global_role="advisor", status="active")
    student = UserFactory(global_role="student", status="active")
    outsider = UserFactory(global_role="student", status="active")
    project = ResearchProject.objects.create(title="Security Membership", advisor=teacher)
    ProjectMembership.objects.create(project=project, user=teacher, role="advisor")

    activation_list = authenticate(api_client, student).get("/api/accounts/admin/role-activations/")
    blocked_add = authenticate(api_client, outsider).post(
        f"/api/projects/{project.id}/members/",
        {"studentId": student.id},
        format="json",
    )
    allowed_view = authenticate(api_client, admin).get("/api/accounts/admin/role-activations/")

    assert activation_list.status_code == 403
    assert blocked_add.status_code in {403, 404}
    assert allowed_view.status_code == 200


@pytest.mark.django_db
def test_upload_download_feedback_resource_notification_and_audit_security(api_client):
    teacher = UserFactory(global_role="advisor", status="active")
    student = UserFactory(global_role="student", status="active")
    outsider = UserFactory(global_role="student", status="active")
    admin = UserFactory(global_role="admin", status="active")
    project = ResearchProject.objects.create(title="Security Matrix", advisor=teacher)
    ProjectMembership.objects.create(project=project, user=teacher, role="advisor")
    ProjectMembership.objects.create(project=project, user=student, role="student")
    category = DocumentCategory.objects.create(name="Security", created_by=teacher)
    document_file = UploadedFileFactory(
        owner=teacher, category="document", original_filename="secure.pdf"
    )
    document = DocumentRecord.objects.create(
        project=project,
        category=category,
        title="Secure Document",
        document_file=document_file,
        checksum_sha256=document_file.checksum_sha256,
        created_by=teacher,
    )
    PaperRecord.objects.create(
        project=project,
        title="Private Paper",
        authors=["Researcher"],
        uploaded_file=UploadedFileFactory(owner=teacher),
        created_by=teacher,
    )
    writing_project = WritingProject.objects.create(
        project=project,
        student=student,
        title="Chapter",
        writing_type=WritingProject.WritingType.THESIS,
    )
    version = WritingVersion.objects.create(
        writing_project=writing_project,
        version_number=1,
        submitted_by=student,
        draft_file=UploadedFileFactory(
            owner=student, category="writing", original_filename="chapter.docx"
        ),
        file_kind=WritingVersion.FileKind.WORD,
    )
    feedback = TeacherFeedback.objects.create(
        writing_version=version,
        reviewer=teacher,
        comments="Reviewed",
        annotated_file=UploadedFileFactory(
            owner=teacher, category="feedback", original_filename="annotated.docx"
        ),
    )
    resource_type = ResourceType.objects.create(name="Instrument")
    resource = ResourceItem.objects.create(resource_type=resource_type, name="Spectrometer")
    submission = ResourceUseSubmission.objects.create(
        resource_item=resource,
        student=student,
        submission_type=ResourceUseSubmission.SubmissionType.REQUEST,
        details="Need access",
    )
    Notification.objects.create(
        project=project,
        recipient=student,
        recipient_email=student.email,
        event_type=Notification.EventType.TEACHER_FEEDBACK_AVAILABLE,
        target_type="TeacherFeedback",
        target_id=str(feedback.id),
        subject="Feedback available",
        eligible_at=timezone.now(),
    )
    AuditEvent.objects.create(
        actor=teacher,
        project=project,
        event_type="verification.sent",
        target_type="EmailVerificationCode",
        target_id="1",
        summary="verification code: 123456 token=raw-secret password=raw-pass",
    )

    invalid_upload = authenticate(api_client, student).post(
        f"/api/projects/{project.id}/papers/",
        {
            "file": SimpleUploadedFile(
                "malware.exe", b"bad", content_type="application/octet-stream"
            )
        },
        format="multipart",
    )
    blocked_download = authenticate(api_client, outsider).get(
        f"/api/documents/{document.id}/download"
    )
    blocked_feedback = authenticate(api_client, outsider).get(
        f"/api/teacher-feedback/{feedback.id}/download"
    )
    blocked_resource = authenticate(api_client, student).patch(
        f"/api/resource-use-submissions/{submission.id}/",
        {"status": "confirmed"},
        format="json",
    )
    visible_notifications = authenticate(api_client, outsider).get("/api/notifications")
    audit_denied = authenticate(api_client, teacher).get("/api/audit-events")
    audit_allowed = authenticate(api_client, admin).get("/api/audit-events")

    assert invalid_upload.status_code in {400, 403}
    assert blocked_download.status_code == 403
    assert blocked_feedback.status_code == 403
    assert blocked_resource.status_code == 403
    assert visible_notifications.status_code == 200
    assert visible_notifications.data["results"] == []
    assert audit_denied.status_code == 403
    assert audit_allowed.status_code == 200
    rendered_summary = audit_allowed.data["results"][0]["summary"]
    assert "123456" not in rendered_summary
    assert "raw-secret" not in rendered_summary
    assert "raw-pass" not in rendered_summary
    assert "[masked]" in rendered_summary
