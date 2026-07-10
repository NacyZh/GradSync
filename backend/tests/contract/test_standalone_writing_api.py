import pytest
from django.core.files.uploadedfile import SimpleUploadedFile

from apps.submissions.models import WritingProject
from tests.factories.shared_workspace import (
    active_admin,
    active_student,
    active_teacher,
    project_with_members,
)
from tests.helpers import authenticate


def _docx(name="draft.docx", body=b"word-draft"):
    return SimpleUploadedFile(
        name,
        body,
        content_type="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
    )


@pytest.mark.django_db
def test_standalone_writing_list_create_version_feedback_contract(api_client):
    student = active_student()
    advisor = active_teacher()
    project_with_members(advisor=advisor, students=[student])
    student_client = authenticate(api_client, student)

    create_response = student_client.post(
        "/api/writing-projects/",
        {"title": "Standalone Thesis", "writingType": WritingProject.WritingType.THESIS},
        format="json",
    )
    list_response = student_client.get("/api/writing-projects/?q=Standalone")
    version_response = student_client.post(
        f"/api/writing-projects/{create_response.data['id']}/versions",
        {"file": _docx(), "summary": "First standalone draft"},
        format="multipart",
    )
    feedback_response = authenticate(api_client, advisor).post(
        f"/api/writing-versions/{version_response.data['id']}/feedback",
        {"annotatedFile": _docx("annotated.docx", b"notes"), "comments": "Revise intro"},
        format="multipart",
    )
    download_response = student_client.get(
        f"/api/teacher-feedback/{feedback_response.data['id']}/download"
    )

    assert create_response.status_code == 201
    assert create_response.data["participantRole"] == "student_author"
    assert create_response.data["legacyProjectId"] in {str(create_response.data["projectId"]), None}
    assert list_response.status_code == 200
    assert [item["title"] for item in list_response.data["results"]] == ["Standalone Thesis"]
    assert version_response.status_code == 201
    assert version_response.data["versionNumber"] == 1
    assert feedback_response.status_code == 201
    assert feedback_response.data["status"] == "notification_pending"
    assert download_response.status_code == 200
    assert download_response.data["filename"] == "annotated.docx"


@pytest.mark.django_db
def test_standalone_writing_denies_unassigned_teacher_without_metadata(api_client):
    student = active_student()
    advisor = active_teacher()
    different_teacher = active_teacher()
    project_with_members(advisor=advisor, students=[student])
    created = authenticate(api_client, student).post(
        "/api/writing-projects/",
        {"title": "Private Thesis", "writingType": WritingProject.WritingType.THESIS},
        format="json",
    )

    list_response = authenticate(api_client, different_teacher).get("/api/writing-projects/")
    version_response = authenticate(api_client, different_teacher).post(
        f"/api/writing-projects/{created.data['id']}/versions",
        {"file": _docx("forbidden.docx")},
        format="multipart",
    )

    assert list_response.status_code == 200
    assert list_response.data["results"] == []
    assert version_response.status_code == 403
    assert "Private Thesis" not in str(version_response.data)


@pytest.mark.django_db
def test_standalone_writing_create_does_not_require_project_membership(api_client):
    student = active_student()
    advisor = active_teacher()

    create_response = authenticate(api_client, student).post(
        "/api/writing-projects/",
        {"title": "No Project Thesis", "writingType": WritingProject.WritingType.THESIS},
        format="json",
    )
    list_response = authenticate(api_client, student).get("/api/writing-projects/")
    advisor_list_response = authenticate(api_client, advisor).get("/api/writing-projects/")

    assert create_response.status_code == 201
    assert create_response.data["participantRole"] == "student_author"
    assert create_response.data["title"] == "No Project Thesis"
    assert [item["title"] for item in list_response.data["results"]] == ["No Project Thesis"]
    assert [item["title"] for item in advisor_list_response.data["results"]] == [
        "No Project Thesis"
    ]


@pytest.mark.django_db
def test_standalone_writing_create_is_student_author_only(api_client):
    advisor = active_teacher()
    admin = active_admin()

    advisor_response = authenticate(api_client, advisor).post(
        "/api/writing-projects/",
        {"title": "Advisor Created", "writingType": WritingProject.WritingType.MANUSCRIPT},
        format="json",
    )
    admin_response = authenticate(api_client, admin).post(
        "/api/writing-projects/",
        {"title": "Admin Created", "writingType": WritingProject.WritingType.MANUSCRIPT},
        format="json",
    )

    assert advisor_response.status_code == 403
    assert admin_response.status_code == 403
