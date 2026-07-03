import pytest

from apps.projects.models import ProjectMembership, ResearchProject
from tests.factories.accounts import UserFactory
from tests.helpers import authenticate


@pytest.mark.django_db
def test_code_artifact_create_version_conflict_and_download_authorization(api_client):
    advisor = UserFactory(global_role="advisor")
    student = UserFactory(global_role="student")
    outsider = UserFactory(global_role="student")
    project = ResearchProject.objects.create(title="Systems Lab", advisor=advisor)
    ProjectMembership.objects.create(project=project, user=student, role="student")

    client = authenticate(api_client, student)
    artifact_response = client.post(
        f"/api/projects/{project.id}/code-artifacts/",
        {"name": "Simulator", "description": "Experiment source", "tags": ["sim"]},
        format="json",
    )
    assert artifact_response.status_code == 201
    artifact_id = artifact_response.data["id"]

    version_response = client.post(
        f"/api/projects/{project.id}/code-artifacts/{artifact_id}/versions/",
        {
            "versionLabel": "v1",
            "commitReference": "abc123",
            "filename": "sim.zip",
            "contentType": "application/zip",
            "sizeBytes": 2048,
            "checksumSha256": "b" * 64,
        },
        format="json",
    )
    assert version_response.status_code == 201

    duplicate_response = client.post(
        f"/api/projects/{project.id}/code-artifacts/{artifact_id}/versions/",
        {
            "versionLabel": "v1",
            "filename": "sim-v1-copy.zip",
            "contentType": "application/zip",
            "sizeBytes": 2048,
            "checksumSha256": "c" * 64,
        },
        format="json",
    )
    assert duplicate_response.status_code == 409

    download_response = client.post(
        f"/api/projects/{project.id}/code-artifacts/{artifact_id}/versions/{version_response.data['id']}/download/"
    )
    assert download_response.status_code == 200
    assert download_response.data["filename"] == "sim.zip"

    outsider_response = authenticate(api_client, outsider).post(
        f"/api/projects/{project.id}/code-artifacts/{artifact_id}/versions/{version_response.data['id']}/download/"
    )
    assert outsider_response.status_code == 403


@pytest.mark.django_db
def test_code_import_rejection_is_enforced_by_policy():
    from django.core.exceptions import ValidationError

    from apps.repositories.upload_policy import validate_code_import

    with pytest.raises(ValidationError):
        validate_code_import(filename="source.zip", size_bytes=201 * 1024 * 1024)

    with pytest.raises(ValidationError):
        validate_code_import(filename="source.exe", content_type="application/octet-stream")
