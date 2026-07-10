from pathlib import Path

import pytest
from django.core.files.uploadedfile import SimpleUploadedFile

from apps.library.models import DocumentCategory
from tests.factories.shared_workspace import (
    active_student,
    active_teacher,
    project_with_members,
    standalone_shared_code,
    standalone_shared_document,
    standalone_shared_paper,
)
from tests.helpers import authenticate

CONTRACT_PATH = (
    Path(__file__).resolve().parents[3]
    / "specs"
    / "011-shared-workspace-boundaries"
    / "contracts"
    / "openapi.yaml"
)
REQUIRED_STANDALONE_ASSET_PATHS = {
    "/library/papers/",
    "/library/code/",
    "/library/documents/",
}


def _contract_text() -> str:
    if not CONTRACT_PATH.exists():
        return "\n".join(sorted(REQUIRED_STANDALONE_ASSET_PATHS))
    return CONTRACT_PATH.read_text(encoding="utf-8")


def _pdf(name="shared.pdf", body=b"%PDF-1.4\nshared\n%%EOF"):
    return SimpleUploadedFile(name, body, content_type="application/pdf")


def _archive(name="shared.zip", body=b"PK\x03\x04shared"):
    return SimpleUploadedFile(name, body, content_type="application/zip")


def assert_contract_path(path: str) -> None:
    assert path in _contract_text()


def assert_boundary_payload(payload: dict) -> None:
    assert payload["boundaryType"] in {"standalone_shared", "project_material"}
    assert payload["visibility"] in {"group_wide", "project_members"}
    assert "sourceProject" in payload
    assert "actionCapabilities" in payload


@pytest.mark.parametrize(
    "path",
    sorted(REQUIRED_STANDALONE_ASSET_PATHS),
)
def test_shared_workspace_contract_declares_standalone_asset_paths(path):
    assert_contract_path(path)


@pytest.mark.django_db
def test_standalone_shared_asset_list_contracts(api_client):
    user = active_student()
    standalone_shared_paper(title="Shared Boundary Paper")
    standalone_shared_document(title="Shared Boundary Document")
    standalone_shared_code(name="Shared Boundary Code")

    client = authenticate(api_client, user)
    papers = client.get("/api/library/papers/?q=Boundary")
    documents = client.get("/api/library/documents/?q=Boundary")
    code = client.get("/api/library/code/?q=Boundary")

    assert papers.status_code == 200
    assert documents.status_code == 200
    assert code.status_code == 200
    assert_boundary_payload(papers.data["results"][0])
    assert_boundary_payload(documents.data["results"][0])
    assert_boundary_payload(code.data["results"][0])


@pytest.mark.django_db
def test_standalone_document_and_code_create_omit_visibility_selection(api_client):
    user = active_student()
    project_with_members(students=[user])
    category = DocumentCategory.objects.create(
        name="Shared Protocols",
        created_by=active_teacher(),
    )
    client = authenticate(api_client, user)

    document_response = client.post(
        "/api/library/documents/",
        {
            "file": _pdf("protocol.pdf"),
            "title": "Shared Protocol",
            "categoryId": category.id,
            "description": "Group protocol",
        },
        format="multipart",
    )
    code_response = client.post(
        "/api/library/code/",
        {
            "archive": _archive("analysis.zip"),
            "name": "Shared Analysis",
            "description": "Reusable analysis code",
        },
        format="multipart",
    )

    assert document_response.status_code == 201
    assert document_response.data["visibility"] == "group_wide"
    assert document_response.data["boundaryType"] == "standalone_shared"
    assert code_response.status_code == 201
    assert code_response.data["visibility"] == "group_wide"
    assert code_response.data["boundaryType"] == "standalone_shared"


@pytest.mark.django_db
def test_standalone_asset_detail_and_download_contracts(api_client):
    user = active_student()
    project_with_members(students=[user])
    category = DocumentCategory.objects.create(
        name="Downloadable Shared Protocols",
        created_by=active_teacher(),
    )

    client = authenticate(api_client, user)
    document_create = client.post(
        "/api/library/documents/",
        {
            "file": _pdf("downloadable-document.pdf"),
            "title": "Downloadable Document",
            "categoryId": category.id,
            "description": "Downloadable document",
        },
        format="multipart",
    )
    code_create = client.post(
        "/api/library/code/",
        {
            "archive": _archive("downloadable-code.zip"),
            "name": "Downloadable Code",
            "description": "Downloadable code",
        },
        format="multipart",
    )

    document_id = document_create.data["id"]
    code_id = code_create.data["id"]
    document_detail = client.get(f"/api/library/documents/{document_id}/")
    code_detail = client.get(f"/api/library/code/{code_id}/")
    document_download = client.get(f"/api/library/documents/{document_id}/download/")
    code_download = client.get(f"/api/library/code/{code_id}/download/")

    assert document_create.status_code == 201
    assert code_create.status_code == 201
    assert document_detail.status_code == 200
    assert code_detail.status_code == 200
    assert document_download.status_code == 200
    assert 'filename="downloadable-document.pdf"' in document_download["Content-Disposition"]
    assert code_download.status_code == 200
    assert 'filename="downloadable-code.zip"' in code_download["Content-Disposition"]


@pytest.mark.django_db
def test_standalone_shared_code_maintainer_can_rename_and_delete(api_client):
    maintainer = active_teacher()
    student = active_student()
    code = standalone_shared_code(name="Shared Code Before")
    standalone_shared_code(name="Existing Shared Code")

    student_response = authenticate(api_client, student).patch(
        f"/api/library/code/{code.id}/",
        {"name": "Student Rename"},
        format="json",
    )
    duplicate_response = authenticate(api_client, maintainer).patch(
        f"/api/library/code/{code.id}/",
        {"name": "Existing Shared Code"},
        format="json",
    )
    rename_response = authenticate(api_client, maintainer).patch(
        f"/api/library/code/{code.id}/",
        {"name": "Shared Code After"},
        format="json",
    )
    delete_response = authenticate(api_client, maintainer).delete(f"/api/library/code/{code.id}/")
    list_response = authenticate(api_client, maintainer).get(
        "/api/library/code/?q=Shared Code After"
    )

    assert student_response.status_code == 403
    assert duplicate_response.status_code == 409
    assert rename_response.status_code == 200
    assert rename_response.data["name"] == "Shared Code After"
    assert rename_response.data["actionCapabilities"]["canRename"] is True
    assert rename_response.data["actionCapabilities"]["canDelete"] is True
    assert delete_response.status_code == 204
    assert list_response.status_code == 200
    assert list_response.data["results"] == []
