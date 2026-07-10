import pytest
from django.core.files.uploadedfile import SimpleUploadedFile

from tests.factories.shared_workspace import active_student, active_teacher, project_with_members
from tests.helpers import authenticate


def _pdf(name="material.pdf"):
    return SimpleUploadedFile(name, b"material", content_type="application/pdf")


@pytest.mark.django_db
def test_project_only_material_is_hidden_from_non_members(api_client):
    advisor = active_teacher()
    student = active_student()
    outsider = active_student()
    project = project_with_members(advisor=advisor, students=[student])
    created = authenticate(api_client, advisor).post(
        f"/api/projects/{project.id}/materials/",
        {
            "materialType": "document",
            "title": "Project Only Protocol",
            "visibility": "project-only",
            "file": _pdf(),
        },
        format="multipart",
    )

    member_response = authenticate(api_client, student).get(
        f"/api/projects/{project.id}/materials/"
    )
    outsider_response = authenticate(api_client, outsider).get(
        f"/api/projects/{project.id}/materials/"
    )

    assert created.status_code == 201
    assert member_response.status_code == 200
    assert [item["displayName"] for item in member_response.data["results"]] == [
        "Project Only Protocol"
    ]
    assert outsider_response.status_code in {403, 404}
    assert "Project Only Protocol" not in str(outsider_response.data)


@pytest.mark.django_db
def test_group_wide_project_document_appears_in_external_shared_documents(api_client):
    advisor = active_teacher()
    student = active_student()
    other_student = active_student()
    project = project_with_members(advisor=advisor, students=[student])
    project_with_members(students=[other_student], title="Other Project")
    created = authenticate(api_client, advisor).post(
        f"/api/projects/{project.id}/materials/",
        {
            "materialType": "document",
            "title": "Shared Project Protocol",
            "visibility": "group-wide",
            "file": _pdf("shared.pdf"),
        },
        format="multipart",
    )

    response = authenticate(api_client, other_student).get("/api/library/documents/")

    assert created.status_code == 201
    assert response.status_code == 200
    assert [item["title"] for item in response.data["results"]] == ["Shared Project Protocol"]
    assert response.data["results"][0]["sourceProject"]["title"] == project.title
