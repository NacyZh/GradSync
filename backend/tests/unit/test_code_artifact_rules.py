import pytest
from django.core.exceptions import ValidationError

from apps.projects.models import ProjectMembership, ResearchProject
from apps.repositories.models import CodeArtifact, CodeArtifactVersion
from apps.repositories.services import CodeArtifactService
from tests.factories.accounts import UserFactory


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
