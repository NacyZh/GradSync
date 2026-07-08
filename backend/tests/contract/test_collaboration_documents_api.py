import pytest
from django.core.files.uploadedfile import SimpleUploadedFile

from apps.audit.models import AuditEvent
from apps.library.models import DocumentRecord
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


@pytest.mark.django_db
def test_document_action_capabilities_for_maintainer_and_non_maintainer(api_client):
    teacher = UserFactory(global_role="advisor", status="active")
    student = UserFactory(global_role="student", status="active")
    project = ResearchProject.objects.create(title="Capability Documents", advisor=teacher)
    ProjectMembership.objects.create(project=project, user=teacher, role="advisor")
    ProjectMembership.objects.create(project=project, user=student, role="student")
    category = (
        authenticate(api_client, teacher)
        .post("/api/document-categories", {"name": "Capability Protocols"})
        .data
    )
    document = authenticate(api_client, student).post(
        f"/api/projects/{project.id}/documents",
        {
            "file": _document("capabilities.pdf"),
            "title": "Capability Protocol",
            "categoryId": category["id"],
        },
        format="multipart",
    )

    maintainer_response = authenticate(api_client, teacher).get(
        f"/api/projects/{project.id}/documents/{document.data['id']}"
    )
    non_maintainer_response = authenticate(api_client, student).get(
        f"/api/projects/{project.id}/documents/{document.data['id']}"
    )

    assert maintainer_response.status_code == 200
    assert maintainer_response.data["actionCapabilities"] == {
        "canView": True,
        "canDownload": True,
        "canRename": True,
        "canDelete": True,
        "canUploadGroupWide": True,
    }
    assert non_maintainer_response.status_code == 200
    assert non_maintainer_response.data["actionCapabilities"] == {
        "canView": True,
        "canDownload": True,
        "canRename": False,
        "canDelete": False,
        "canUploadGroupWide": False,
    }


@pytest.mark.django_db
def test_document_list_and_retrieve_exclude_archived_records(api_client):
    teacher = UserFactory(global_role="advisor", status="active")
    student = UserFactory(global_role="student", status="active")
    project = ResearchProject.objects.create(title="Archived Documents", advisor=teacher)
    ProjectMembership.objects.create(project=project, user=teacher, role="advisor")
    ProjectMembership.objects.create(project=project, user=student, role="student")
    category = (
        authenticate(api_client, teacher)
        .post("/api/document-categories", {"name": "Archived Protocols"})
        .data
    )
    active_response = authenticate(api_client, student).post(
        f"/api/projects/{project.id}/documents",
        {
            "file": _document("active.pdf"),
            "title": "Active Protocol",
            "categoryId": category["id"],
        },
        format="multipart",
    )
    archived_response = authenticate(api_client, student).post(
        f"/api/projects/{project.id}/documents",
        {
            "file": _document("archived.pdf"),
            "title": "Archived Protocol",
            "categoryId": category["id"],
        },
        format="multipart",
    )
    DocumentRecord.objects.filter(pk=archived_response.data["id"]).update(
        status=DocumentRecord.Status.ARCHIVED
    )

    list_response = authenticate(api_client, teacher).get(
        f"/api/projects/{project.id}/documents?q=Protocol"
    )
    active_detail = authenticate(api_client, teacher).get(
        f"/api/projects/{project.id}/documents/{active_response.data['id']}"
    )
    archived_detail = authenticate(api_client, teacher).get(
        f"/api/projects/{project.id}/documents/{archived_response.data['id']}"
    )

    assert list_response.status_code == 200
    assert [item["title"] for item in list_response.data["results"]] == ["Active Protocol"]
    assert active_detail.status_code == 200
    assert archived_detail.status_code == 404


@pytest.mark.django_db
def test_document_upload_accepts_file_and_category_without_title(api_client):
    teacher = UserFactory(global_role="advisor", status="active")
    student = UserFactory(global_role="student", status="active")
    project = ResearchProject.objects.create(title="Optional Title Documents", advisor=teacher)
    ProjectMembership.objects.create(project=project, user=teacher, role="advisor")
    ProjectMembership.objects.create(project=project, user=student, role="student")
    category = (
        authenticate(api_client, teacher)
        .post("/api/document-categories", {"name": "Optional Title Protocols"})
        .data
    )

    response = authenticate(api_client, student).post(
        f"/api/projects/{project.id}/documents",
        {
            "file": _document("../../Unsafe <Protocol>.pdf"),
            "categoryId": category["id"],
            "description": "Filename-derived title",
        },
        format="multipart",
    )

    assert response.status_code == 201
    assert response.data["title"] == "Unsafe Protocol .pdf"
    assert response.data["description"] == "Filename-derived title"
    assert response.data["visibility"] == "project_members"


@pytest.mark.django_db
def test_document_group_wide_upload_requires_project_maintainer(api_client):
    teacher = UserFactory(global_role="advisor", status="active")
    student = UserFactory(global_role="student", status="active")
    project = ResearchProject.objects.create(title="Group Wide Documents", advisor=teacher)
    ProjectMembership.objects.create(project=project, user=teacher, role="advisor")
    ProjectMembership.objects.create(project=project, user=student, role="student")
    category = (
        authenticate(api_client, teacher)
        .post("/api/document-categories", {"name": "Group Wide Protocols"})
        .data
    )

    blocked = authenticate(api_client, student).post(
        f"/api/projects/{project.id}/documents",
        {
            "file": _document("student-group.pdf"),
            "categoryId": category["id"],
            "visibility": "group_wide",
        },
        format="multipart",
    )
    allowed = authenticate(api_client, teacher).post(
        f"/api/projects/{project.id}/documents",
        {
            "file": _document("teacher-group.pdf"),
            "categoryId": category["id"],
            "visibility": "group_wide",
        },
        format="multipart",
    )

    assert blocked.status_code == 403
    assert allowed.status_code == 201
    assert allowed.data["visibility"] == "group_wide"


@pytest.mark.django_db
def test_document_rename_contract_validates_permissions_conflicts_and_audit(api_client):
    teacher = UserFactory(global_role="advisor", status="active")
    student = UserFactory(global_role="student", status="active")
    project = ResearchProject.objects.create(title="Rename Documents", advisor=teacher)
    ProjectMembership.objects.create(project=project, user=teacher, role="advisor")
    ProjectMembership.objects.create(project=project, user=student, role="student")
    category = (
        authenticate(api_client, teacher)
        .post("/api/document-categories", {"name": "Rename Protocols"})
        .data
    )
    first = authenticate(api_client, teacher).post(
        f"/api/projects/{project.id}/documents",
        {"file": _document("first.pdf"), "categoryId": category["id"], "title": "First"},
        format="multipart",
    )
    second = authenticate(api_client, teacher).post(
        f"/api/projects/{project.id}/documents",
        {"file": _document("second.pdf"), "categoryId": category["id"], "title": "Second"},
        format="multipart",
    )

    renamed = authenticate(api_client, teacher).patch(
        f"/api/projects/{project.id}/documents/{first.data['id']}",
        {"newTitle": "Renamed First", "reason": "Clarify title"},
        format="json",
    )
    invalid = authenticate(api_client, teacher).patch(
        f"/api/projects/{project.id}/documents/{first.data['id']}",
        {"newTitle": "   "},
        format="json",
    )
    duplicate = authenticate(api_client, teacher).patch(
        f"/api/projects/{project.id}/documents/{first.data['id']}",
        {"newTitle": " second "},
        format="json",
    )
    blocked = authenticate(api_client, student).patch(
        f"/api/projects/{project.id}/documents/{first.data['id']}",
        {"newTitle": "Student Rename"},
        format="json",
    )
    DocumentRecord.objects.filter(pk=second.data["id"]).update(status=DocumentRecord.Status.ARCHIVED)
    archived = authenticate(api_client, teacher).patch(
        f"/api/projects/{project.id}/documents/{second.data['id']}",
        {"newTitle": "Archived Rename"},
        format="json",
    )

    assert renamed.status_code == 200
    assert renamed.data["title"] == "Renamed First"
    assert invalid.status_code == 400
    assert duplicate.status_code == 409
    assert blocked.status_code == 403
    assert archived.status_code == 409
    assert AuditEvent.objects.filter(event_type="document.renamed", actor=teacher).exists()
    assert AuditEvent.objects.filter(event_type="document.rename.rejected", actor=student).exists()


@pytest.mark.django_db
def test_document_delete_contract_archives_and_restricts_actions(api_client):
    teacher = UserFactory(global_role="advisor", status="active")
    student = UserFactory(global_role="student", status="active")
    project = ResearchProject.objects.create(title="Delete Documents", advisor=teacher)
    ProjectMembership.objects.create(project=project, user=teacher, role="advisor")
    ProjectMembership.objects.create(project=project, user=student, role="student")
    category = (
        authenticate(api_client, teacher)
        .post("/api/document-categories", {"name": "Delete Protocols"})
        .data
    )
    document = authenticate(api_client, teacher).post(
        f"/api/projects/{project.id}/documents",
        {"file": _document("delete.pdf"), "categoryId": category["id"], "title": "Delete Me"},
        format="multipart",
    )
    blocked_doc = authenticate(api_client, teacher).post(
        f"/api/projects/{project.id}/documents",
        {"file": _document("blocked.pdf"), "categoryId": category["id"], "title": "Blocked"},
        format="multipart",
    )

    blocked = authenticate(api_client, student).delete(
        f"/api/projects/{project.id}/documents/{blocked_doc.data['id']}",
        format="json",
    )
    deleted = authenticate(api_client, teacher).delete(
        f"/api/projects/{project.id}/documents/{document.data['id']}",
        {"reason": "Superseded"},
        format="json",
    )
    list_response = authenticate(api_client, teacher).get(
        f"/api/projects/{project.id}/documents?q=Delete Me"
    )
    direct_detail = authenticate(api_client, teacher).get(
        f"/api/projects/{project.id}/documents/{document.data['id']}"
    )

    assert blocked.status_code == 403
    assert deleted.status_code == 204
    assert list_response.status_code == 200
    assert "Delete Me" not in [item["title"] for item in list_response.data["results"]]
    assert direct_detail.status_code == 404
    assert DocumentRecord.objects.get(pk=document.data["id"]).status == DocumentRecord.Status.ARCHIVED
    assert AuditEvent.objects.filter(event_type="document.deleted", actor=teacher).exists()
    assert AuditEvent.objects.filter(event_type="document.delete.rejected", actor=student).exists()
