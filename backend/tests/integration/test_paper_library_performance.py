import time

import pytest

from apps.library.models import PaperRecord
from apps.projects.models import ResearchProject
from tests.factories.accounts import UserFactory
from tests.helpers import authenticate


@pytest.mark.django_db
def test_shared_paper_search_is_paginated_and_excludes_unavailable_records(api_client):
    advisor = UserFactory(global_role="advisor", status="active")
    requester = UserFactory(global_role="student", status="active")
    project = ResearchProject.objects.create(title="Paper Scale", advisor=advisor)
    PaperRecord.objects.bulk_create(
        [
            PaperRecord(
                project=project,
                title=f"Graph Search Paper {index:03d}",
                canonical_title=f"Graph Search Paper {index:03d}",
                normalized_title=f"graph search paper {index:03d}",
                title_source="legacy",
                title_confidence="high",
                authors=["Ada Lovelace"],
                publication_year=2026,
                tags=["graph", "scale"],
                created_by=advisor,
                status=PaperRecord.Status.ACTIVE,
            )
            for index in range(75)
        ]
        + [
            PaperRecord(
                project=project,
                title="Graph Deleted Paper",
                canonical_title="Graph Deleted Paper",
                normalized_title="graph deleted paper",
                title_source="legacy",
                title_confidence="high",
                authors=["Ada Lovelace"],
                created_by=advisor,
                status=PaperRecord.Status.DELETED,
            ),
            PaperRecord(
                project=project,
                title="Graph Invalid Paper",
                canonical_title="Graph Invalid Paper",
                normalized_title="graph invalid paper",
                title_source="legacy",
                title_confidence="high",
                authors=["Ada Lovelace"],
                created_by=advisor,
                status=PaperRecord.Status.INVALID,
            ),
        ]
    )

    started_at = time.monotonic()
    response = authenticate(api_client, requester).get(
        "/api/library/papers/?q=Graph&page_size=25&page=1"
    )
    elapsed = time.monotonic() - started_at

    assert response.status_code == 200
    assert response.data["count"] == 75
    assert len(response.data["results"]) == 25
    assert all(item["status"] == PaperRecord.Status.ACTIVE for item in response.data["results"])
    assert elapsed < 2
