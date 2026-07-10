import pytest
from django.core.files.uploadedfile import SimpleUploadedFile

from apps.submissions.models import WritingParticipant
from tests.factories.shared_workspace import (
    active_admin,
    active_student,
    active_teacher,
    writing_item,
)
from tests.helpers import authenticate


def _docx(name="draft.docx"):
    return SimpleUploadedFile(
        name,
        b"draft",
        content_type="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
    )


@pytest.mark.django_db
def test_standalone_writing_access_matrix_has_no_unrelated_metadata(api_client):
    student = active_student()
    advisor = active_teacher()
    reviewer = active_teacher()
    different_teacher = active_teacher()
    unrelated_student = active_student()
    admin = active_admin()
    writing = writing_item(student=student, title="Private Boundary Draft")
    WritingParticipant.objects.create(
        writing_project=writing,
        user=advisor,
        participant_role=WritingParticipant.Role.BOUND_ADVISOR,
    )
    WritingParticipant.objects.create(
        writing_project=writing,
        user=reviewer,
        participant_role=WritingParticipant.Role.ASSIGNED_REVIEWER,
    )

    allowed_users = [student, advisor, reviewer, admin]
    for user in allowed_users:
        response = authenticate(api_client, user).get("/api/writing-projects/")
        assert response.status_code == 200
        assert [item["title"] for item in response.data["results"]] == ["Private Boundary Draft"]

    for user in [different_teacher, unrelated_student]:
        response = authenticate(api_client, user).get("/api/writing-projects/")
        assert response.status_code == 200
        assert response.data["results"] == []
        assert "Private Boundary Draft" not in str(response.data)


@pytest.mark.django_db
def test_only_student_author_uploads_versions_and_assigned_reviewer_submits_feedback(api_client):
    student = active_student()
    reviewer = active_teacher()
    different_teacher = active_teacher()
    writing = writing_item(student=student)
    WritingParticipant.objects.create(
        writing_project=writing,
        user=reviewer,
        participant_role=WritingParticipant.Role.ASSIGNED_REVIEWER,
    )

    blocked_version = authenticate(api_client, reviewer).post(
        f"/api/writing-projects/{writing.id}/versions",
        {"file": _docx("reviewer.docx")},
        format="multipart",
    )
    version = authenticate(api_client, student).post(
        f"/api/writing-projects/{writing.id}/versions",
        {"file": _docx("student.docx")},
        format="multipart",
    )
    allowed_feedback = authenticate(api_client, reviewer).post(
        f"/api/writing-versions/{version.data['id']}/feedback",
        {"annotatedFile": _docx("annotated.docx"), "comments": "Reviewed"},
        format="multipart",
    )
    blocked_feedback = authenticate(api_client, different_teacher).post(
        f"/api/writing-versions/{version.data['id']}/feedback",
        {"annotatedFile": _docx("hidden.docx"), "comments": "No access"},
        format="multipart",
    )

    assert blocked_version.status_code == 403
    assert version.status_code == 201
    assert allowed_feedback.status_code == 201
    assert blocked_feedback.status_code == 403
    assert writing.title not in str(blocked_feedback.data)
