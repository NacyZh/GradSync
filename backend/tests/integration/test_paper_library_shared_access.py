import pytest

from apps.library.models import PaperRecord
from apps.projects.models import ResearchProject
from tests.factories.accounts import UserFactory
from tests.helpers import authenticate


def _paper(*, advisor, title="Shared Graph Paper", status=PaperRecord.Status.ACTIVE):
    project = ResearchProject.objects.create(title=f"Project for {title}", advisor=advisor)
    return PaperRecord.objects.create(
        project=project,
        title=title,
        canonical_title=title,
        normalized_title=title.lower().replace(" ", "-"),
        title_source="legacy",
        title_confidence="high",
        authors=["Ada Lovelace"],
        publication_year=2026,
        tags=["graph", "collaboration"],
        created_by=advisor,
        status=status,
    )


@pytest.mark.django_db
def test_active_users_without_shared_project_membership_can_list_and_view_shared_papers(
    api_client,
):
    advisor_a = UserFactory(global_role="advisor", status="active")
    advisor_b = UserFactory(global_role="advisor", status="active")
    user_a = UserFactory(global_role="student", status="active")
    user_b = UserFactory(global_role="student", status="active")
    paper = _paper(advisor=advisor_a, title="Graph Neural Methods")
    _paper(advisor=advisor_b, title="Deleted Legacy Paper", status=PaperRecord.Status.DELETED)
    _paper(advisor=advisor_b, title="Invalid Legacy Paper", status=PaperRecord.Status.INVALID)

    response_a = authenticate(api_client, user_a).get("/api/library/papers/?q=Graph")
    response_b = authenticate(api_client, user_b).get(f"/api/library/papers/{paper.id}/")

    assert response_a.status_code == 200
    assert [item["id"] for item in response_a.data["results"]] == [paper.id]
    assert response_b.status_code == 200
    assert response_b.data["canonicalTitle"] == "Graph Neural Methods"


@pytest.mark.django_db
def test_shared_paper_library_denies_anonymous_and_inactive_accounts(api_client):
    advisor = UserFactory(global_role="advisor", status="active")
    paper = _paper(advisor=advisor)
    inactive_user = UserFactory(global_role="student", status="suspended")

    anonymous_response = api_client.get("/api/library/papers/")
    inactive_list_response = authenticate(api_client, inactive_user).get("/api/library/papers/")
    inactive_detail_response = authenticate(api_client, inactive_user).get(
        f"/api/library/papers/{paper.id}/"
    )

    assert anonymous_response.status_code in {401, 403}
    assert inactive_list_response.status_code == 403
    assert inactive_detail_response.status_code == 403
