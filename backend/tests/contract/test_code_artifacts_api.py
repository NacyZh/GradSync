import pytest

from apps.audit.models import AuditEvent
from apps.projects.models import ProjectMembership, ResearchProject
from apps.repositories.models import CodeArtifact
from tests.factories.accounts import UserFactory
from tests.factories.collaboration import active_code_artifact, archived_code_artifact
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
    assert download_response.status_code == 410

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


@pytest.mark.django_db
def test_code_artifact_list_excludes_archived_and_retrieve_returns_action_capabilities(api_client):
    advisor = UserFactory(global_role="advisor", status="active")
    student = UserFactory(global_role="student", status="active")
    admin = UserFactory(global_role="admin", status="active")
    project = ResearchProject.objects.create(title="Capabilities", advisor=advisor)
    ProjectMembership.objects.create(project=project, user=advisor, role="advisor")
    ProjectMembership.objects.create(project=project, user=student, role="student")
    active = active_code_artifact(project=project, name="Active Repo", created_by=student)
    archived = archived_code_artifact(project=project, name="Archived Repo", created_by=student)

    student_client = authenticate(api_client, student)
    list_response = student_client.get(f"/api/projects/{project.id}/code-artifacts/")
    assert list_response.status_code == 200
    assert [item["name"] for item in list_response.data["results"]] == ["Active Repo"]
    assert list_response.data["results"][0]["actionCapabilities"] == {
        "canView": True,
        "canDownload": True,
        "canRename": False,
        "canDelete": False,
    }

    advisor_response = authenticate(api_client, advisor).get(
        f"/api/projects/{project.id}/code-artifacts/{active.id}/"
    )
    assert advisor_response.status_code == 200
    assert advisor_response.data["actionCapabilities"]["canRename"] is True
    assert advisor_response.data["actionCapabilities"]["canDelete"] is True

    admin_response = authenticate(api_client, admin).get(
        f"/api/projects/{project.id}/code-artifacts/{active.id}/"
    )
    assert admin_response.status_code == 200
    assert admin_response.data["actionCapabilities"]["canRename"] is True

    archived_response = student_client.get(
        f"/api/projects/{project.id}/code-artifacts/{archived.id}/"
    )
    assert archived_response.status_code == 404


@pytest.mark.django_db
def test_group_wide_archived_code_artifact_is_excluded_for_non_member(api_client):
    advisor = UserFactory(global_role="advisor", status="active")
    outsider = UserFactory(global_role="student", status="active")
    project = ResearchProject.objects.create(title="Archived Shared", advisor=advisor)
    ProjectMembership.objects.create(project=project, user=advisor, role="advisor")
    active_code_artifact(
        project=project,
        name="Shared Active",
        visibility=CodeArtifact.Visibility.GROUP_WIDE,
        created_by=advisor,
    )
    archived_code_artifact(
        project=project,
        name="Shared Archived",
        visibility=CodeArtifact.Visibility.GROUP_WIDE,
        created_by=advisor,
    )

    response = authenticate(api_client, outsider).get(
        f"/api/projects/{project.id}/code-artifacts/?q=Shared"
    )

    assert response.status_code == 200
    assert [item["name"] for item in response.data["results"]] == ["Shared Active"]


@pytest.mark.django_db
def test_code_artifact_patch_rename_authorization_validation_and_audit(api_client):
    advisor = UserFactory(global_role="advisor", status="active")
    student = UserFactory(global_role="student", status="active")
    other_advisor = UserFactory(global_role="advisor", status="active")
    project = ResearchProject.objects.create(title="Rename API", advisor=advisor)
    ProjectMembership.objects.create(project=project, user=advisor, role="advisor")
    ProjectMembership.objects.create(project=project, user=student, role="student")
    artifact = active_code_artifact(project=project, name="Original Repo", created_by=student)
    active_code_artifact(project=project, name="Existing Repo", created_by=advisor)
    archived = archived_code_artifact(project=project, name="Archived Repo", created_by=student)

    student_response = authenticate(api_client, student).patch(
        f"/api/projects/{project.id}/code-artifacts/{artifact.id}/",
        {"name": "Student Rename"},
        format="json",
    )
    assert student_response.status_code == 403
    assert AuditEvent.objects.filter(
        actor=student,
        target_id=str(artifact.id),
        event_type="code_artifact.rename.rejected",
    ).exists()

    unrelated_advisor_response = authenticate(api_client, other_advisor).patch(
        f"/api/projects/{project.id}/code-artifacts/{artifact.id}/",
        {"name": "Other Advisor Rename"},
        format="json",
    )
    assert unrelated_advisor_response.status_code == 403

    blank_response = authenticate(api_client, advisor).patch(
        f"/api/projects/{project.id}/code-artifacts/{artifact.id}/",
        {"name": "   "},
        format="json",
    )
    assert blank_response.status_code == 400

    duplicate_response = authenticate(api_client, advisor).patch(
        f"/api/projects/{project.id}/code-artifacts/{artifact.id}/",
        {"name": "Existing Repo"},
        format="json",
    )
    assert duplicate_response.status_code == 409

    archived_response = authenticate(api_client, advisor).patch(
        f"/api/projects/{project.id}/code-artifacts/{archived.id}/",
        {"name": "Archived Rename"},
        format="json",
    )
    assert archived_response.status_code == 409

    rename_response = authenticate(api_client, advisor).patch(
        f"/api/projects/{project.id}/code-artifacts/{artifact.id}/",
        {"name": "Renamed Repo", "reason": "clearer label"},
        format="json",
    )

    artifact.refresh_from_db()
    assert rename_response.status_code == 200
    assert rename_response.data["name"] == "Renamed Repo"
    assert rename_response.data["actionCapabilities"]["canRename"] is True
    assert artifact.name == "Renamed Repo"
    assert AuditEvent.objects.filter(
        actor=advisor,
        target_id=str(artifact.id),
        event_type="code_artifact.renamed",
    ).exists()


@pytest.mark.django_db
def test_code_artifact_delete_soft_deletes_and_removes_ordinary_availability(api_client):
    advisor = UserFactory(global_role="advisor", status="active")
    admin = UserFactory(global_role="admin", status="active")
    student = UserFactory(global_role="student", status="active")
    project = ResearchProject.objects.create(title="Delete API", advisor=advisor)
    ProjectMembership.objects.create(project=project, user=advisor, role="advisor")
    ProjectMembership.objects.create(project=project, user=student, role="student")
    artifact = active_code_artifact(project=project, name="Delete Me", created_by=student)
    admin_artifact = active_code_artifact(project=project, name="Admin Remove", created_by=student)

    student_response = authenticate(api_client, student).delete(
        f"/api/projects/{project.id}/code-artifacts/{artifact.id}/"
    )
    assert student_response.status_code == 403
    assert AuditEvent.objects.filter(
        actor=student,
        target_id=str(artifact.id),
        event_type="code_artifact.delete.rejected",
    ).exists()

    delete_response = authenticate(api_client, advisor).delete(
        f"/api/projects/{project.id}/code-artifacts/{artifact.id}/"
    )
    artifact.refresh_from_db()
    assert delete_response.status_code == 204
    assert artifact.status == CodeArtifact.Status.ARCHIVED
    assert artifact.archived_at is not None
    assert AuditEvent.objects.filter(
        actor=advisor,
        target_id=str(artifact.id),
        event_type="code_artifact.deleted",
    ).exists()

    list_response = authenticate(api_client, student).get(
        f"/api/projects/{project.id}/code-artifacts/?q=Delete"
    )
    direct_download_response = authenticate(api_client, student).get(
        f"/api/code-artifacts/{artifact.id}/download"
    )
    repeated_response = authenticate(api_client, advisor).delete(
        f"/api/projects/{project.id}/code-artifacts/{artifact.id}/"
    )

    assert list_response.status_code == 200
    assert list_response.data["results"] == []
    assert direct_download_response.status_code == 404
    assert repeated_response.status_code == 409

    admin_response = authenticate(api_client, admin).delete(
        f"/api/projects/{project.id}/code-artifacts/{admin_artifact.id}/"
    )
    admin_artifact.refresh_from_db()
    assert admin_response.status_code == 204
    assert admin_artifact.status == CodeArtifact.Status.ARCHIVED
