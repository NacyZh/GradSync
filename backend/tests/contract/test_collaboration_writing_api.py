import pytest
from django.core.files.uploadedfile import SimpleUploadedFile

from apps.projects.models import ProjectMembership, ResearchProject
from tests.factories.accounts import UserFactory
from tests.helpers import authenticate


def _docx(name="draft.docx", body=b"word-draft"):
    return SimpleUploadedFile(
        name,
        body,
        content_type="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
    )


@pytest.mark.django_db
def test_writing_project_version_feedback_and_download_contract(api_client):
    teacher = UserFactory(global_role="advisor", status="active")
    student = UserFactory(global_role="student", status="active")
    project = ResearchProject.objects.create(title="Writing Contract", advisor=teacher)
    ProjectMembership.objects.create(project=project, user=teacher, role="advisor")
    ProjectMembership.objects.create(project=project, user=student, role="student")

    student_client = authenticate(api_client, student)
    project_response = student_client.post(
        f"/api/projects/{project.id}/writing-projects/",
        {"title": "Thesis Chapter", "writingType": "thesis"},
    )
    version_response = student_client.post(
        f"/api/writing-projects/{project_response.data['id']}/versions",
        {"file": _docx(), "summary": "First complete draft"},
        format="multipart",
    )
    feedback_response = authenticate(api_client, teacher).post(
        f"/api/writing-versions/{version_response.data['id']}/feedback",
        {
            "annotatedFile": _docx("annotated.docx", b"advisor-notes"),
            "comments": "Please revise section two.",
        },
        format="multipart",
    )
    download_response = student_client.get(
        f"/api/teacher-feedback/{feedback_response.data['id']}/download"
    )

    assert project_response.status_code == 201
    assert project_response.data["writingType"] == "thesis"
    assert version_response.status_code == 201
    assert version_response.data["versionNumber"] == 1
    assert version_response.data["fileKind"] == "word"
    assert feedback_response.status_code == 201
    assert feedback_response.data["status"] == "notification_pending"
    assert feedback_response.data["notificationStatus"] == "pending"
    assert download_response.status_code == 200
    assert download_response.data["filename"] == "annotated.docx"


@pytest.mark.django_db
def test_writing_upload_validation_and_feedback_authorization_contract(api_client):
    teacher = UserFactory(global_role="advisor", status="active")
    student = UserFactory(global_role="student", status="active")
    outsider = UserFactory(global_role="student", status="active")
    project = ResearchProject.objects.create(title="Writing Validation", advisor=teacher)
    ProjectMembership.objects.create(project=project, user=teacher, role="advisor")
    ProjectMembership.objects.create(project=project, user=student, role="student")
    client = authenticate(api_client, student)

    writing_project = client.post(
        f"/api/projects/{project.id}/writing-projects/",
        {"title": "Manuscript", "writingType": "manuscript"},
    )
    invalid = client.post(
        f"/api/writing-projects/{writing_project.data['id']}/versions",
        {"file": SimpleUploadedFile("draft.exe", b"bad", content_type="application/octet-stream")},
        format="multipart",
    )
    valid = client.post(
        f"/api/writing-projects/{writing_project.data['id']}/versions",
        {"file": SimpleUploadedFile("draft.tex", b"\\section{Intro}", content_type="text/x-tex")},
        format="multipart",
    )
    outsider_feedback = authenticate(api_client, outsider).post(
        f"/api/writing-versions/{valid.data['id']}/feedback",
        {"annotatedFile": _docx("outsider.docx"), "comments": "No access"},
        format="multipart",
    )

    assert invalid.status_code == 400
    assert valid.status_code == 201
    assert valid.data["fileKind"] == "latex_source"
    assert outsider_feedback.status_code in {403, 404}
