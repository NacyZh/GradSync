import pytest
from django.core.files.uploadedfile import SimpleUploadedFile

from apps.audit.models import AuditEvent, DownloadEvent
from apps.library.models import DocumentCategory, DocumentRecord
from apps.projects.models import ProjectMembership, ResearchProject
from tests.factories.accounts import UserFactory
from tests.helpers import authenticate


def _file(name: str, body: bytes = b"document"):
    content_type = "text/markdown" if name.endswith(".md") else "application/pdf"
    return SimpleUploadedFile(name, body, content_type=content_type)


@pytest.mark.django_db
def test_category_validation_document_search_visibility_and_download_audit(api_client):
    teacher = UserFactory(global_role="advisor", status="active")
    student = UserFactory(global_role="student", status="active")
    outsider = UserFactory(global_role="student", status="active")
    project = ResearchProject.objects.create(title="Documents", advisor=teacher)
    ProjectMembership.objects.create(project=project, user=teacher, role="advisor")
    ProjectMembership.objects.create(project=project, user=student, role="student")

    teacher_client = authenticate(api_client, teacher)
    protocols = teacher_client.post(
        "/api/document-categories",
        {"name": "Protocols", "description": "Operating procedures"},
    ).data
    reports = teacher_client.post(
        "/api/document-categories",
        {"name": "Reports", "description": "Research reports"},
    ).data
    duplicate_category = teacher_client.post(
        "/api/document-categories",
        {"name": "Protocols"},
    )

    protocol_upload = authenticate(api_client, student).post(
        f"/api/projects/{project.id}/documents",
        {
            "file": _file("microscope.md", b"# Microscope"),
            "title": "Microscope Setup",
            "categoryId": protocols["id"],
            "description": "Microscope calibration protocol",
        },
        format="multipart",
    )
    group_upload = authenticate(api_client, teacher).post(
        f"/api/projects/{project.id}/documents",
        {
            "file": _file("annual.pdf", b"%PDF annual"),
            "title": "Annual Group Report",
            "categoryId": reports["id"],
            "description": "Reusable report",
            "visibility": "group_wide",
        },
        format="multipart",
    )
    missing_category = authenticate(api_client, student).post(
        f"/api/projects/{project.id}/documents",
        {"file": _file("missing.pdf"), "title": "Missing", "categoryId": 99999},
        format="multipart",
    )
    invalid_file = authenticate(api_client, student).post(
        f"/api/projects/{project.id}/documents",
        {
            "file": SimpleUploadedFile("bad.exe", b"bad", content_type="application/octet-stream"),
            "title": "Bad",
            "categoryId": protocols["id"],
        },
        format="multipart",
    )
    student_group_wide = authenticate(api_client, student).post(
        f"/api/projects/{project.id}/documents",
        {
            "file": _file("share.pdf", b"%PDF share"),
            "title": "Student Share Attempt",
            "categoryId": reports["id"],
            "visibility": "group_wide",
        },
        format="multipart",
    )

    assert duplicate_category.status_code == 400
    assert protocol_upload.status_code == 201
    assert group_upload.status_code == 201
    assert missing_category.status_code == 400
    assert invalid_file.status_code == 400
    assert student_group_wide.status_code == 403

    record = DocumentRecord.objects.get(pk=protocol_upload.data["id"])
    assert record.document_file is not None
    assert record.checksum_sha256 == record.document_file.checksum_sha256
    assert record.category.name == "Protocols"

    category_response = authenticate(api_client, student).get(
        f"/api/projects/{project.id}/documents?categoryId={protocols['id']}"
    )
    search_response = authenticate(api_client, student).get(
        f"/api/projects/{project.id}/documents?q=calibration"
    )
    outsider_response = authenticate(api_client, outsider).get(
        f"/api/projects/{project.id}/documents?q=Report"
    )
    download_response = authenticate(api_client, student).get(
        f"/api/documents/{record.id}/download"
    )

    assert category_response.status_code == 200
    assert [item["title"] for item in category_response.data["results"]] == [
        "Microscope Setup"
    ]
    assert search_response.status_code == 200
    assert search_response.data["results"][0]["title"] == "Microscope Setup"
    assert outsider_response.status_code == 200
    assert outsider_response.data["results"][0]["title"] == "Annual Group Report"
    assert download_response.status_code == 200
    assert DownloadEvent.objects.filter(
        actor=student,
        target_id=str(record.document_file_id),
    ).exists()
    assert AuditEvent.objects.filter(actor=student, event_type="document.downloaded").exists()


@pytest.mark.django_db
def test_category_list_returns_active_categories(api_client):
    teacher = UserFactory(global_role="advisor", status="active")
    DocumentCategory.objects.create(name="Protocols", created_by=teacher)
    DocumentCategory.objects.create(
        name="Archived",
        created_by=teacher,
        status=DocumentCategory.Status.ARCHIVED,
    )

    response = authenticate(api_client, teacher).get("/api/document-categories")

    assert response.status_code == 200
    assert [category["name"] for category in response.data] == ["Protocols"]
