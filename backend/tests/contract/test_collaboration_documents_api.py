import pytest
from django.core.files.uploadedfile import SimpleUploadedFile

from apps.projects.models import ProjectMembership, ResearchProject
from tests.factories.accounts import UserFactory
from tests.helpers import authenticate


def _document(name="protocol.pdf", body=b"%PDF-1.4\nprotocol\n%%EOF"):
    return SimpleUploadedFile(name, body, content_type="application/pdf")


@pytest.mark.django_db
def test_document_category_upload_search_and_download_contract(api_client):
    teacher = UserFactory(global_role="advisor", status="active")
    student = UserFactory(global_role="student", status="active")
    project = ResearchProject.objects.create(title="Document Library", advisor=teacher)
    ProjectMembership.objects.create(project=project, user=teacher, role="advisor")
    ProjectMembership.objects.create(project=project, user=student, role="student")

    category_response = authenticate(api_client, teacher).post(
        "/api/document-categories",
        {"name": "Protocols", "description": "Lab operating documents"},
    )
    upload_response = authenticate(api_client, student).post(
        f"/api/projects/{project.id}/documents",
        {
            "file": _document(),
            "title": "Microscope Protocol",
            "categoryId": category_response.data["id"],
            "description": "Shared microscope setup",
        },
        format="multipart",
    )
    list_response = authenticate(api_client, teacher).get(
        f"/api/projects/{project.id}/documents?q=microscope&categoryId={category_response.data['id']}"
    )
    download_response = authenticate(api_client, teacher).get(
        f"/api/documents/{upload_response.data['id']}/download"
    )

    assert category_response.status_code == 201
    assert upload_response.status_code == 201
    assert upload_response.data["categoryId"] == str(category_response.data["id"])
    assert upload_response.data["visibility"] == "project_members"
    assert upload_response.data["checksumSha256"]
    assert list_response.status_code == 200
    assert list_response.data["results"][0]["title"] == "Microscope Protocol"
    assert download_response.status_code == 200
    assert download_response.data["filename"] == "protocol.pdf"


@pytest.mark.django_db
def test_document_visibility_and_upload_validation_contract(api_client):
    teacher = UserFactory(global_role="advisor", status="active")
    student = UserFactory(global_role="student", status="active")
    outsider = UserFactory(global_role="student", status="active")
    project = ResearchProject.objects.create(title="Private Documents", advisor=teacher)
    ProjectMembership.objects.create(project=project, user=teacher, role="advisor")
    ProjectMembership.objects.create(project=project, user=student, role="student")
    category = (
        authenticate(api_client, teacher)
        .post(
            "/api/document-categories",
            {"name": "Reports"},
        )
        .data
    )

    scoped_response = authenticate(api_client, student).post(
        f"/api/projects/{project.id}/documents",
        {
            "file": _document("scoped.pdf"),
            "title": "Scoped Report",
            "categoryId": category["id"],
        },
        format="multipart",
    )
    group_wide_response = authenticate(api_client, teacher).post(
        f"/api/projects/{project.id}/documents",
        {
            "file": _document("group.pdf"),
            "title": "Group Report",
            "categoryId": category["id"],
            "visibility": "group_wide",
        },
        format="multipart",
    )
    invalid_response = authenticate(api_client, student).post(
        f"/api/projects/{project.id}/documents",
        {
            "file": SimpleUploadedFile(
                "malware.exe", b"bad", content_type="application/octet-stream"
            ),
            "title": "Bad Report",
            "categoryId": category["id"],
        },
        format="multipart",
    )
    missing_category = authenticate(api_client, student).post(
        f"/api/projects/{project.id}/documents",
        {"file": _document("missing.pdf"), "title": "Missing Category"},
        format="multipart",
    )

    outsider_client = authenticate(api_client, outsider)
    visible_response = outsider_client.get(f"/api/projects/{project.id}/documents?q=Report")
    blocked_download = outsider_client.get(f"/api/documents/{scoped_response.data['id']}/download")

    assert scoped_response.status_code == 201
    assert group_wide_response.status_code == 201
    assert invalid_response.status_code == 400
    assert missing_category.status_code == 400
    assert visible_response.status_code == 200
    assert [item["title"] for item in visible_response.data["results"]] == ["Group Report"]
    assert blocked_download.status_code == 403
