import pytest
from django.core.exceptions import ValidationError

from apps.projects.models import ProjectMembership, ResearchProject
from apps.repositories.models import CodeArtifact, CodeArtifactVersion
from apps.repositories.services import (
    CodeArtifactService,
    can_manage_code_artifact,
    is_seeded_code_sample,
)
from tests.factories.accounts import UserFactory
from tests.factories.collaboration import archived_code_artifact


@pytest.mark.django_db
def test_code_artifact_version_reference_uniqueness_across_statuses():
    user = UserFactory()
    project = ResearchProject.objects.create(title="Project", advisor=user)
    ProjectMembership.objects.create(project=project, user=user, role="student")
    artifact = CodeArtifact.objects.create(project=project, name="Repo", created_by=user)
    CodeArtifactVersion.objects.create(
        artifact=artifact,
        project=project,
        version_label="v1",
        commit_reference="abc",
        filename="repo.zip",
        storage_key="repo.zip",
        checksum_sha256="e" * 64,
        imported_by=user,
        status=CodeArtifactVersion.Status.ARCHIVED,
    )

    service = CodeArtifactService(user, project)
    with pytest.raises(ValidationError):
        service.import_version(
            artifact,
            version_label="v1",
            filename="repo2.zip",
            checksum_sha256="f" * 64,
            size_bytes=10,
            content_type="application/zip",
        )

    with pytest.raises(ValidationError):
        service.import_version(
            artifact,
            commit_reference="abc",
            filename="repo3.zip",
            checksum_sha256="a" * 64,
            size_bytes=10,
            content_type="application/zip",
        )


@pytest.mark.django_db
def test_code_artifact_manage_permission_allows_project_advisor_and_admin_only():
    project_advisor = UserFactory(global_role="advisor", status="active")
    admin = UserFactory(global_role="admin", status="active")
    student = UserFactory(global_role="student", status="active")
    other_advisor = UserFactory(global_role="advisor", status="active")
    project = ResearchProject.objects.create(title="Managed Code", advisor=project_advisor)
    ProjectMembership.objects.create(project=project, user=project_advisor, role="advisor")
    ProjectMembership.objects.create(project=project, user=student, role="student")
    artifact = CodeArtifact.objects.create(project=project, name="Repo", created_by=student)

    assert can_manage_code_artifact(project_advisor, artifact)
    assert can_manage_code_artifact(admin, artifact)
    assert not can_manage_code_artifact(student, artifact)
    assert not can_manage_code_artifact(other_advisor, artifact)


@pytest.mark.django_db
def test_code_artifact_manage_permission_rejects_inactive_and_archived_artifacts():
    project_advisor = UserFactory(global_role="advisor", status="active")
    project = ResearchProject.objects.create(title="Archived Code", advisor=project_advisor)
    ProjectMembership.objects.create(project=project, user=project_advisor, role="advisor")
    archived = archived_code_artifact(project=project, created_by=project_advisor)
    inactive_project = ResearchProject.objects.create(
        title="Inactive Project",
        advisor=project_advisor,
        status=ResearchProject.Status.ARCHIVED,
    )
    inactive_project.memberships.create(user=project_advisor, role="advisor")
    inactive_artifact = CodeArtifact.objects.create(
        project=inactive_project,
        name="Inactive Repo",
        created_by=project_advisor,
    )

    assert not can_manage_code_artifact(project_advisor, archived)
    assert not can_manage_code_artifact(project_advisor, inactive_artifact)


@pytest.mark.django_db
def test_seeded_code_sample_matcher_requires_exact_known_identity():
    advisor = UserFactory(global_role="advisor", status="active")
    project = ResearchProject.objects.create(title="Seeded Code", advisor=advisor)
    exact = CodeArtifact.objects.create(
        project=project,
        name="Simulator",
        source_path_label="team-library/code/simulator",
        created_by=advisor,
    )
    CodeArtifactVersion.objects.create(
        artifact=exact,
        project=project,
        version_label="v1",
        storage_key="e2e/sim.zip",
        filename="sim.zip",
        checksum_sha256="b" * 64,
        imported_by=advisor,
    )
    similar_name = CodeArtifact.objects.create(
        project=project,
        name="Simulator",
        source_path_label="user-uploads/code/simulator",
        created_by=advisor,
    )
    CodeArtifactVersion.objects.create(
        artifact=similar_name,
        project=project,
        version_label="v1",
        storage_key="user/sim.zip",
        filename="sim.zip",
        checksum_sha256="b" * 64,
        imported_by=advisor,
    )
    similar_version = CodeArtifact.objects.create(
        project=project,
        name="Simulator",
        source_path_label="team-library/code/simulator",
        created_by=advisor,
    )
    CodeArtifactVersion.objects.create(
        artifact=similar_version,
        project=project,
        version_label="v1",
        storage_key="e2e/sim-copy.zip",
        filename="sim.zip",
        checksum_sha256="b" * 64,
        imported_by=advisor,
    )

    assert is_seeded_code_sample(exact)
    assert not is_seeded_code_sample(similar_name)
    assert not is_seeded_code_sample(similar_version)
