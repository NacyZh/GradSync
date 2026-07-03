import pytest

from apps.audit.models import DownloadEvent
from apps.library.models import PaperAttachment, PaperRecord
from apps.projects.models import ProjectMembership, ResearchProject
from apps.repositories.models import CodeArtifact, CodeArtifactVersion
from tests.factories.accounts import UserFactory
from tests.helpers import authenticate


@pytest.mark.django_db
def test_research_asset_search_download_isolation_and_audit(api_client):
    member = UserFactory()
    outsider = UserFactory()
    advisor = UserFactory(global_role="advisor")
    project = ResearchProject.objects.create(title="Project A", advisor=advisor)
    other_project = ResearchProject.objects.create(title="Project B", advisor=advisor)
    ProjectMembership.objects.create(project=project, user=member, role="student")
    ProjectMembership.objects.create(project=other_project, user=outsider, role="student")
    paper = PaperRecord.objects.create(
        project=project,
        title="Private Paper",
        authors=["A"],
        publication_year=2026,
        created_by=member,
    )
    PaperAttachment.objects.create(
        paper=paper,
        project=project,
        storage_key="private.pdf",
        filename="private.pdf",
        checksum_sha256="1" * 64,
        imported_by=member,
    )
    artifact = CodeArtifact.objects.create(project=project, name="Private Code", created_by=member)
    version = CodeArtifactVersion.objects.create(
        artifact=artifact,
        project=project,
        version_label="v1",
        filename="private.zip",
        storage_key="private.zip",
        checksum_sha256="2" * 64,
        imported_by=member,
    )

    member_client = authenticate(api_client, member)
    paper_list = member_client.get(f"/api/projects/{project.id}/papers/?q=Private")
    assert paper_list.status_code == 200
    assert len(paper_list.data["results"]) == 1

    code_list = member_client.get(f"/api/projects/{project.id}/code-artifacts/?q=Private")
    assert code_list.status_code == 200
    assert len(code_list.data["results"]) == 1

    member_client.post(f"/api/projects/{project.id}/papers/{paper.id}/download/")
    member_client.post(
        f"/api/projects/{project.id}/code-artifacts/{artifact.id}/versions/{version.id}/download/"
    )
    assert DownloadEvent.objects.filter(project=project).count() == 2

    outsider_client = authenticate(api_client, outsider)
    outsider_papers = outsider_client.get(f"/api/projects/{project.id}/papers/?q=Private")
    assert outsider_papers.status_code == 200
    assert outsider_papers.data["results"] == []
    assert (
        outsider_client.post(f"/api/projects/{project.id}/papers/{paper.id}/download/").status_code
        == 403
    )
    outsider_code = outsider_client.get(f"/api/projects/{project.id}/code-artifacts/?q=Private")
    assert outsider_code.status_code == 200
    assert outsider_code.data["results"] == []
    assert (
        outsider_client.post(
            f"/api/projects/{project.id}/code-artifacts/{artifact.id}/versions/{version.id}/download/"
        ).status_code
        == 403
    )
