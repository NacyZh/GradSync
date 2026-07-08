import time

import pytest

from apps.library.duplicate_services import find_duplicate
from apps.library.models import PaperRecord
from apps.projects.models import ProjectMembership, ResearchProject
from apps.repositories.models import CodeArtifact
from tests.factories.accounts import UserFactory
from tests.helpers import authenticate


@pytest.mark.django_db
def test_research_asset_search_and_duplicate_detection_performance(api_client):
    user = UserFactory()
    project = ResearchProject.objects.create(title="Performance", advisor=user)
    ProjectMembership.objects.create(project=project, user=user, role="advisor")
    papers = [
        PaperRecord(
            project=project,
            title=f"Paper {index}",
            authors=[f"Author {index}"],
            publication_year=2020 + (index % 5),
            tags=["performance", f"tag-{index % 10}"],
            fingerprint=f"paper {index}|author {index}|{2020 + (index % 5)}",
            created_by=user,
        )
        for index in range(1000)
    ]
    PaperRecord.objects.bulk_create(papers)
    CodeArtifact.objects.bulk_create(
        [
            CodeArtifact(
                project=project,
                name=f"Code {index}",
                tags=["performance", f"tag-{index % 10}"],
                created_by=user,
            )
            for index in range(250)
        ]
    )

    client = authenticate(api_client, user)
    start = time.monotonic()
    papers_response = client.get(f"/api/projects/{project.id}/papers/?q=Paper")
    code_response = client.get(f"/api/projects/{project.id}/code-artifacts/?q=Code")
    elapsed = time.monotonic() - start

    assert papers_response.status_code == 200
    assert code_response.status_code == 200
    assert elapsed < 2

    start = time.monotonic()
    for index in range(100):
        find_duplicate(
            project,
            title=f"Paper {index}",
            authors=[f"Author {index}"],
            publication_year=2020 + (index % 5),
        )
    assert time.monotonic() - start < 10


@pytest.mark.django_db
def test_paper_search_under_seeded_scale_uses_pagination(api_client):
    user = UserFactory()
    project = ResearchProject.objects.create(title="Paper Scale", advisor=user)
    ProjectMembership.objects.create(project=project, user=user, role="advisor")
    PaperRecord.objects.bulk_create(
        [
            PaperRecord(
                project=project,
                title=f"Collaboration Paper {index}",
                authors=[f"Researcher {index % 20}"],
                publication_year=2020 + (index % 5),
                tags=["collaboration", f"topic-{index % 25}"],
                visibility="project_members",
                fingerprint=(
                    f"collaboration paper {index}|researcher {index % 20}|{2020 + (index % 5)}"
                ),
                created_by=user,
            )
            for index in range(1000)
        ]
    )

    client = authenticate(api_client, user)
    start = time.monotonic()
    response = client.get(f"/api/projects/{project.id}/papers/?q=Collaboration&page_size=50")
    elapsed = time.monotonic() - start

    assert response.status_code == 200
    assert len(response.data["results"]) == 50
    assert elapsed < 2


@pytest.mark.django_db
def test_code_artifact_search_under_seeded_scale_uses_pagination(api_client):
    user = UserFactory()
    project = ResearchProject.objects.create(title="Code Scale", advisor=user)
    ProjectMembership.objects.create(project=project, user=user, role="advisor")
    CodeArtifact.objects.bulk_create(
        [
            CodeArtifact(
                project=project,
                name=f"Archive {index}",
                description=f"Searchable archive for simulation workflow {index}",
                tags=["simulation", f"topic-{index % 25}"],
                visibility="project_members",
                created_by=user,
            )
            for index in range(1000)
        ]
        + [
            CodeArtifact(
                project=project,
                name=f"Archive archived {index}",
                description=f"Archived searchable archive {index}",
                tags=["simulation", "archived"],
                visibility="project_members",
                status=CodeArtifact.Status.ARCHIVED,
                created_by=user,
            )
            for index in range(25)
        ]
    )
    assert any(
        list(index.fields) == ["project", "visibility", "status"]
        for index in CodeArtifact._meta.indexes
    )

    client = authenticate(api_client, user)
    start = time.monotonic()
    response = client.get(f"/api/projects/{project.id}/code-artifacts/?q=Archive&page_size=50")
    elapsed = time.monotonic() - start

    assert response.status_code == 200
    assert len(response.data["results"]) == 50
    assert response.data["count"] == 1000
    assert all(item["status"] == CodeArtifact.Status.ACTIVE for item in response.data["results"])
    assert elapsed < 2
