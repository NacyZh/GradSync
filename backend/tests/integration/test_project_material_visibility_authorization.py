import pytest
from django.core.files.uploadedfile import SimpleUploadedFile

from tests.factories.shared_workspace import active_student, active_teacher, project_with_members
from tests.helpers import authenticate


def _pdf(name="ordinary.pdf"):
    return SimpleUploadedFile(name, b"ordinary", content_type="application/pdf")


@pytest.mark.django_db
def test_ordinary_project_member_cannot_create_group_wide_material(api_client):
    advisor = active_teacher()
    student = active_student()
    project = project_with_members(advisor=advisor, students=[student])

    response = authenticate(api_client, student).post(
        f"/api/projects/{project.id}/materials/",
        {
            "materialType": "document",
            "title": "Student Shared Attempt",
            "visibility": "group-wide",
            "file": _pdf(),
        },
        format="multipart",
    )

    assert response.status_code == 403
    assert "Student Shared Attempt" not in str(response.data)


@pytest.mark.django_db
def test_ordinary_project_member_material_capabilities_hide_visibility_control(api_client):
    advisor = active_teacher()
    student = active_student()
    project = project_with_members(advisor=advisor, students=[student])
    created = authenticate(api_client, advisor).post(
        f"/api/projects/{project.id}/materials/",
        {
            "materialType": "document",
            "title": "Advisor Protocol",
            "visibility": "project-only",
            "file": _pdf("advisor.pdf"),
        },
        format="multipart",
    )

    response = authenticate(api_client, student).get(f"/api/projects/{project.id}/materials/")

    assert created.status_code == 201
    assert response.status_code == 200
    assert response.data["results"][0]["actionCapabilities"]["canChangeVisibility"] is False
