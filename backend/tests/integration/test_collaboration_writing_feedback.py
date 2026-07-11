import pytest
from django.core.files.storage import default_storage
from django.core.files.uploadedfile import SimpleUploadedFile

from apps.audit.models import AuditEvent, DownloadEvent
from apps.notifications.models import Notification
from apps.projects.models import ProjectMembership, ResearchProject
from apps.submissions.models import (
    TeacherFeedback,
    WritingParticipant,
    WritingProject,
    WritingVersion,
)
from tests.factories.accounts import UserFactory
from tests.helpers import authenticate


def _upload(name: str, body: bytes = b"draft"):
    return SimpleUploadedFile(name, body, content_type="application/octet-stream")


@pytest.mark.django_db
def test_independent_writing_project_histories_and_immutable_versions(api_client):
    teacher = UserFactory(global_role="advisor", status="active")
    student = UserFactory(global_role="student", status="active")
    project = ResearchProject.objects.create(title="Writing Histories", advisor=teacher)
    ProjectMembership.objects.create(project=project, user=teacher, role="advisor")
    ProjectMembership.objects.create(project=project, user=student, role="student")
    client = authenticate(api_client, student)

    thesis = client.post(
        f"/api/projects/{project.id}/writing-projects/",
        {"title": "Thesis", "writingType": "thesis"},
    ).data
    paper = client.post(
        f"/api/projects/{project.id}/writing-projects/",
        {"title": "Paper", "writingType": "paper"},
    ).data

    thesis_v1 = client.post(
        f"/api/writing-projects/{thesis['id']}/versions",
        {"file": _upload("chapter.docx", b"v1"), "summary": "Chapter one"},
        format="multipart",
    )
    thesis_v2 = client.post(
        f"/api/writing-projects/{thesis['id']}/versions",
        {"file": _upload("chapter2.docx", b"v2"), "summary": "Chapter two"},
        format="multipart",
    )
    paper_v1 = client.post(
        f"/api/writing-projects/{paper['id']}/versions",
        {"file": _upload("paper.tex", b"\\section{Paper}")},
        format="multipart",
    )
    list_response = client.get(f"/api/projects/{project.id}/writing-projects/")

    assert thesis_v1.data["versionNumber"] == 1
    assert thesis_v2.data["versionNumber"] == 2
    assert paper_v1.data["versionNumber"] == 1
    histories = {item["title"]: item["versions"] for item in list_response.data["results"]}
    assert [version["versionNumber"] for version in histories["Thesis"]] == [2, 1]
    assert [version["versionNumber"] for version in histories["Paper"]] == [1]
    assert (
        WritingVersion.objects.get(pk=thesis_v1.data["id"]).draft_file.original_filename
        == "chapter.docx"
    )


@pytest.mark.django_db
def test_feedback_authorization_validation_notification_and_download_audit(api_client):
    teacher = UserFactory(global_role="advisor", status="active")
    student = UserFactory(global_role="student", status="active")
    other_student = UserFactory(global_role="student", status="active")
    project = ResearchProject.objects.create(title="Feedback", advisor=teacher)
    ProjectMembership.objects.create(project=project, user=teacher, role="advisor")
    ProjectMembership.objects.create(project=project, user=student, role="student")
    ProjectMembership.objects.create(project=project, user=other_student, role="student")

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
    upload_response = authenticate(api_client, student).post(
        f"/api/writing-projects/{writing_project.id}/versions",
        {"file": _upload("chapter.docx", b"chapter")},
        format="multipart",
    )
    version = WritingVersion.objects.get(pk=upload_response.data["id"])
    draft_download = authenticate(api_client, teacher).get(
        f"/api/writing-versions/{version.id}/download"
    )
    version.refresh_from_db()

    invalid = authenticate(api_client, teacher).post(
        f"/api/writing-versions/{version.id}/feedback",
        {"annotatedFile": _upload("annotated.exe", b"bad"), "comments": "Invalid"},
        format="multipart",
    )
    feedback_response = authenticate(api_client, teacher).post(
        f"/api/writing-versions/{version.id}/feedback",
        {"annotatedFile": _upload("annotated.docx", b"notes"), "comments": "Actionable notes"},
        format="multipart",
    )
    blocked_download = authenticate(api_client, other_student).get(
        f"/api/teacher-feedback/{feedback_response.data['id']}/download"
    )
    download = authenticate(api_client, student).get(
        f"/api/teacher-feedback/{feedback_response.data['id']}/download"
    )

    assert draft_download.status_code == 200
    assert 'filename="chapter.docx"' in draft_download["Content-Disposition"]
    assert version.status == WritingVersion.Status.UNDER_REVIEW
    assert invalid.status_code == 400
    assert feedback_response.status_code == 201
    feedback = TeacherFeedback.objects.get(pk=feedback_response.data["id"])
    assert feedback.notification.status == Notification.Status.PENDING
    assert feedback.writing_version.status == WritingVersion.Status.FEEDBACK_AVAILABLE
    assert blocked_download.status_code == 403
    assert download.status_code == 200
    assert DownloadEvent.objects.filter(
        actor=student, target_id=str(feedback.annotated_file_id)
    ).exists()
    assert AuditEvent.objects.filter(event_type="feedback.submitted", actor=teacher).exists()
    assert AuditEvent.objects.filter(
        event_type="teacher_feedback.downloaded", actor=student
    ).exists()


@pytest.mark.django_db
def test_missing_feedback_file_returns_gone_without_success_download_audit(api_client):
    teacher = UserFactory(global_role="advisor", status="active")
    student = UserFactory(global_role="student", status="active")
    project = ResearchProject.objects.create(title="Missing Feedback", advisor=teacher)
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
        {"file": _upload("chapter.docx", b"chapter")},
        format="multipart",
    )
    feedback_response = authenticate(api_client, teacher).post(
        f"/api/writing-versions/{version_response.data['id']}/feedback",
        {"annotatedFile": _upload("annotated.docx", b"notes"), "comments": "Actionable notes"},
        format="multipart",
    )
    feedback = TeacherFeedback.objects.get(pk=feedback_response.data["id"])
    if default_storage.exists(feedback.annotated_file.stored_name):
        default_storage.delete(feedback.annotated_file.stored_name)

    download = authenticate(api_client, student).get(
        f"/api/teacher-feedback/{feedback.id}/download"
    )

    assert download.status_code == 410
    assert not DownloadEvent.objects.filter(
        actor=student, target_id=str(feedback.annotated_file_id)
    ).exists()
    assert not AuditEvent.objects.filter(
        event_type="teacher_feedback.downloaded", actor=student
    ).exists()


@pytest.mark.django_db
def test_missing_writing_version_file_returns_gone_without_success_download_audit(api_client):
    teacher = UserFactory(global_role="advisor", status="active")
    student = UserFactory(global_role="student", status="active")
    project = ResearchProject.objects.create(title="Missing Draft", advisor=teacher)
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
        {"file": _upload("chapter.docx", b"chapter")},
        format="multipart",
    )
    version = WritingVersion.objects.get(pk=version_response.data["id"])
    if default_storage.exists(version.draft_file.stored_name):
        default_storage.delete(version.draft_file.stored_name)

    download = authenticate(api_client, teacher).get(
        f"/api/writing-versions/{version.id}/download"
    )
    version.refresh_from_db()

    assert download.status_code == 410
    assert version.status == WritingVersion.Status.SUBMITTED
    assert not DownloadEvent.objects.filter(
        actor=teacher, target_id=str(version.draft_file_id)
    ).exists()
    assert not AuditEvent.objects.filter(
        event_type="writing_version.downloaded", actor=teacher
    ).exists()
