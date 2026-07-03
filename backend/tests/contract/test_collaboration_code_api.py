import pytest
from django.core.files.uploadedfile import SimpleUploadedFile

from apps.projects.models import ProjectMembership, ResearchProject
from tests.factories.accounts import UserFactory
from tests.helpers import authenticate


def _archive(name="source.zip", body: bytes | None = None):
    return SimpleUploadedFile(
        name,
        body or f"PK\x03\x04{name}".encode(),
        content_type="application/zip",
    )


@pytest.mark.django_db
def test_code_artifact_upload_list_and_download_contract(api_client):
    teacher = UserFactory(global_role="advisor", status="active")
    student = UserFactory(global_role="student", status="active")
    project = ResearchProject.objects.create(title="Code Project", advisor=teacher)
    ProjectMembership.objects.create(project=project, user=teacher, role="advisor")
    ProjectMembership.objects.create(project=project, user=student, role="student")
    client = authenticate(api_client, student)

    upload_response = client.post(
        f"/api/projects/{project.id}/code-artifacts/",
        {
            "archive": _archive(),
            "name": "Simulation Toolkit",
            "description": "Reusable simulation source archive",
            "tags": "simulation,python",
        },
        format="multipart",
    )
    list_response = client.get(f"/api/projects/{project.id}/code-artifacts/?q=simulation")
    download_response = client.get(f"/api/code-artifacts/{upload_response.data['id']}/download")

    assert upload_response.status_code == 201
    assert upload_response.data["visibility"] == "project_members"
    assert upload_response.data["checksumSha256"]
    assert list_response.status_code == 200
    assert list_response.data["results"][0]["name"] == "Simulation Toolkit"
    assert download_response.status_code == 200
    assert download_response.data["filename"] == "source.zip"


@pytest.mark.django_db
def test_code_artifact_visibility_and_upload_validation_contract(api_client):
    teacher = UserFactory(global_role="advisor", status="active")
    student = UserFactory(global_role="student", status="active")
    outsider = UserFactory(global_role="student", status="active")
    project = ResearchProject.objects.create(title="Code Visibility", advisor=teacher)
    ProjectMembership.objects.create(project=project, user=teacher, role="advisor")
    ProjectMembership.objects.create(project=project, user=student, role="student")

    student_client = authenticate(api_client, student)
    scoped_response = student_client.post(
        f"/api/projects/{project.id}/code-artifacts/",
        {
            "archive": _archive("private.zip"),
            "name": "Private Code",
            "description": "Private archive",
        },
        format="multipart",
    )
    missing_description = student_client.post(
        f"/api/projects/{project.id}/code-artifacts/",
        {"archive": _archive("missing.zip"), "name": "Missing Description"},
        format="multipart",
    )
    invalid_response = student_client.post(
        f"/api/projects/{project.id}/code-artifacts/",
        {
            "archive": SimpleUploadedFile("source.txt", b"not archive", content_type="text/plain"),
            "name": "Bad Code",
            "description": "Bad archive",
        },
        format="multipart",
    )
    group_wide_response = authenticate(api_client, teacher).post(
        f"/api/projects/{project.id}/code-artifacts/",
        {
            "archive": _archive("group.zip"),
            "name": "Group Code",
            "description": "Shared archive",
            "visibility": "group_wide",
        },
        format="multipart",
    )

    outsider_client = authenticate(api_client, outsider)
    visible_response = outsider_client.get(f"/api/projects/{project.id}/code-artifacts/?q=Code")
    blocked_download = outsider_client.get(
        f"/api/code-artifacts/{scoped_response.data['id']}/download"
    )

    assert scoped_response.status_code == 201
    assert missing_description.status_code == 400
    assert invalid_response.status_code == 400
    assert group_wide_response.status_code == 201
    assert [artifact["name"] for artifact in visible_response.data["results"]] == ["Group Code"]
    assert blocked_download.status_code == 403
