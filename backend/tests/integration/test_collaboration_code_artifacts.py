import pytest
from django.core.files.uploadedfile import SimpleUploadedFile

from apps.audit.models import AuditEvent, DownloadEvent
from apps.projects.models import ProjectMembership, ResearchProject
from apps.repositories.models import CodeArtifact
from tests.factories.accounts import UserFactory
from tests.helpers import authenticate


def _archive(name: str, body: bytes | None = None):
    return SimpleUploadedFile(
        name, body or f"PK\x03\x04{name}".encode(), content_type="application/zip"
    )


@pytest.mark.django_db
def test_archive_upload_required_description_search_visibility_and_download_audit(api_client):
    teacher = UserFactory(global_role="advisor", status="active")
    student = UserFactory(global_role="student", status="active")
    outsider = UserFactory(global_role="student", status="active")
    project = ResearchProject.objects.create(title="Archive Project", advisor=teacher)
    ProjectMembership.objects.create(project=project, user=teacher, role="advisor")
    ProjectMembership.objects.create(project=project, user=student, role="student")
    client = authenticate(api_client, student)

    response = client.post(
        f"/api/projects/{project.id}/code-artifacts/",
        {
            "archive": _archive("analysis.zip"),
            "name": "Analysis Pipeline",
            "description": "Pipeline for microscopy image analysis",
            "tags": "analysis,python",
        },
        format="multipart",
    )
    assert response.status_code == 201

    artifact = CodeArtifact.objects.get(pk=response.data["id"])
    assert artifact.archive_file is not None
    assert artifact.description == "Pipeline for microscopy image analysis"
    assert artifact.visibility == "project_members"
    assert artifact.checksum_sha256 == artifact.archive_file.checksum_sha256

    search_response = client.get(f"/api/projects/{project.id}/code-artifacts/?q=microscopy")
    assert search_response.status_code == 200
    assert [item["name"] for item in search_response.data["results"]] == ["Analysis Pipeline"]

    download_response = client.get(f"/api/code-artifacts/{artifact.id}/download")
    assert download_response.status_code == 200
    assert DownloadEvent.objects.filter(
        actor=student, target_id=str(artifact.archive_file_id)
    ).exists()
    assert AuditEvent.objects.filter(actor=student, event_type="code_artifact.downloaded").exists()

    hidden_response = authenticate(api_client, outsider).get(
        f"/api/projects/{project.id}/code-artifacts/?q=microscopy"
    )
    assert hidden_response.status_code == 200
    assert hidden_response.data["results"] == []


@pytest.mark.django_db
def test_group_wide_code_artifact_is_visible_to_non_member_and_student_cannot_share(api_client):
    teacher = UserFactory(global_role="advisor", status="active")
    student = UserFactory(global_role="student", status="active")
    outsider = UserFactory(global_role="student", status="active")
    project = ResearchProject.objects.create(title="Shared Code", advisor=teacher)
    ProjectMembership.objects.create(project=project, user=teacher, role="advisor")
    ProjectMembership.objects.create(project=project, user=student, role="student")

    student_response = authenticate(api_client, student).post(
        f"/api/projects/{project.id}/code-artifacts/",
        {
            "archive": _archive("student.zip"),
            "name": "Student Shared Attempt",
            "description": "Attempted group-wide share",
            "visibility": "group_wide",
        },
        format="multipart",
    )
    teacher_response = authenticate(api_client, teacher).post(
        f"/api/projects/{project.id}/code-artifacts/",
        {
            "archive": _archive("teacher.zip"),
            "name": "Teacher Shared Archive",
            "description": "Reusable group-wide archive",
            "visibility": "group_wide",
        },
        format="multipart",
    )
    outsider_response = authenticate(api_client, outsider).get(
        f"/api/projects/{project.id}/code-artifacts/?q=Reusable"
    )

    assert student_response.status_code == 403
    assert teacher_response.status_code == 201
    assert outsider_response.status_code == 200
    assert outsider_response.data["results"][0]["visibility"] == "group_wide"


@pytest.mark.django_db
def test_non_archive_missing_description_and_duplicate_checksum_are_rejected(api_client):
    teacher = UserFactory(global_role="advisor", status="active")
    project = ResearchProject.objects.create(title="Archive Validation", advisor=teacher)
    ProjectMembership.objects.create(project=project, user=teacher, role="advisor")
    client = authenticate(api_client, teacher)

    first = client.post(
        f"/api/projects/{project.id}/code-artifacts/",
        {
            "archive": _archive("first.zip", b"same-archive"),
            "name": "First",
            "description": "First archive",
        },
        format="multipart",
    )
    duplicate = client.post(
        f"/api/projects/{project.id}/code-artifacts/",
        {
            "archive": _archive("duplicate.zip", b"same-archive"),
            "name": "Duplicate",
            "description": "Duplicate archive",
        },
        format="multipart",
    )
    missing_description = client.post(
        f"/api/projects/{project.id}/code-artifacts/",
        {"archive": _archive("missing.zip"), "name": "Missing"},
        format="multipart",
    )
    invalid = client.post(
        f"/api/projects/{project.id}/code-artifacts/",
        {
            "archive": SimpleUploadedFile("bad.py", b"print(1)", content_type="text/x-python"),
            "name": "Bad",
            "description": "Bad",
        },
        format="multipart",
    )

    assert first.status_code == 201
    assert duplicate.status_code == 409
    assert duplicate.data["message"] == "Code artifact checksum already exists in this project"
    assert missing_description.status_code == 400
    assert invalid.status_code == 400
