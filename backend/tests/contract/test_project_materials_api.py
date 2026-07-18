import pytest
from django.core.files.base import ContentFile
from django.core.files.storage import default_storage
from django.core.files.uploadedfile import SimpleUploadedFile

from apps.projects.models import ProjectMaterial
from tests.factories.shared_workspace import (
    active_student,
    active_teacher,
    project_only_document,
    project_with_members,
)
from tests.helpers import authenticate


def _pdf(name="protocol.pdf", body=b"project-material"):
    return SimpleUploadedFile(name, body, content_type="application/pdf")


def _put_file(storage_key: str, content: bytes = b"project material"):
    if default_storage.exists(storage_key):
        default_storage.delete(storage_key)
    default_storage.save(storage_key, ContentFile(content))


@pytest.mark.django_db
def test_project_materials_list_create_and_visibility_contract(api_client):
    advisor = active_teacher()
    student = active_student()
    project = project_with_members(advisor=advisor, students=[student])
    advisor_client = authenticate(api_client, advisor)

    create_response = advisor_client.post(
        f"/api/projects/{project.id}/materials/",
        {
            "materialType": "document",
            "title": "Project Protocol",
            "visibility": "project-only",
            "file": _pdf(),
        },
        format="multipart",
    )
    list_response = advisor_client.get(f"/api/projects/{project.id}/materials/")
    visibility_response = advisor_client.patch(
        f"/api/projects/{project.id}/materials/{create_response.data['id']}/visibility/",
        {"visibility": "group-wide", "reason": "Share with group"},
        format="json",
    )

    assert create_response.status_code == 201
    assert create_response.data["materialType"] == "document"
    assert create_response.data["sourceProject"]["id"] == str(project.id)
    assert create_response.data["visibility"] == "project-only"
    assert create_response.data["actionCapabilities"]["canChangeVisibility"] is True
    assert list_response.status_code == 200
    assert list_response.data["count"] == 1
    assert visibility_response.status_code == 200
    assert visibility_response.data["visibility"] == "group-wide"


@pytest.mark.django_db
def test_project_material_visibility_change_denies_ordinary_member(api_client):
    advisor = active_teacher()
    student = active_student()
    project = project_with_members(advisor=advisor, students=[student])
    material = authenticate(api_client, advisor).post(
        f"/api/projects/{project.id}/materials/",
        {
            "materialType": "document",
            "title": "Private Protocol",
            "visibility": "project-only",
            "file": _pdf("private.pdf"),
        },
        format="multipart",
    )

    response = authenticate(api_client, student).patch(
        f"/api/projects/{project.id}/materials/{material.data['id']}/visibility/",
        {"visibility": "group-wide"},
        format="json",
    )

    assert response.status_code == 403


@pytest.mark.django_db
def test_project_material_download_contract_authorized_for_file_response(api_client):
    advisor = active_teacher()
    student = active_student()
    project = project_with_members(advisor=advisor, students=[student])
    document = project_only_document(project)
    _put_file(document.document_file.stored_name)
    material = ProjectMaterial.objects.create(
        source_project=project,
        material_type=ProjectMaterial.MaterialType.DOCUMENT,
        backing_record_id=document.id,
        visibility_state=ProjectMaterial.VisibilityState.PROJECT_ONLY,
        classification_state=ProjectMaterial.ClassificationState.ACTIVE,
        classification_reason=ProjectMaterial.ClassificationReason.EXPLICIT_PROJECT_SPECIFIC,
        created_by=advisor,
    )

    response = authenticate(api_client, student).post(
        f"/api/projects/{project.id}/materials/{material.id}/download/"
    )

    assert response.status_code == 200
    assert response.headers["Content-Disposition"].startswith("attachment;")


@pytest.mark.django_db
def test_project_material_download_contract_denies_outsider_and_stale_material(api_client):
    advisor = active_teacher()
    outsider = active_student()
    project = project_with_members(advisor=advisor)
    material = ProjectMaterial.objects.create(
        source_project=project,
        material_type=ProjectMaterial.MaterialType.DOCUMENT,
        backing_record_id=999999,
        visibility_state=ProjectMaterial.VisibilityState.PROJECT_ONLY,
        classification_state=ProjectMaterial.ClassificationState.ACTIVE,
        classification_reason=ProjectMaterial.ClassificationReason.EXPLICIT_PROJECT_SPECIFIC,
        created_by=advisor,
    )

    outsider_response = authenticate(api_client, outsider).post(
        f"/api/projects/{project.id}/materials/{material.id}/download/"
    )
    stale_response = authenticate(api_client, advisor).post(
        f"/api/projects/{project.id}/materials/{material.id}/download/"
    )

    assert outsider_response.status_code in {403, 404}
    assert stale_response.status_code == 410
