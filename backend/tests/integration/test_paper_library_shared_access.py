import pytest

from apps.library.models import PaperLibraryActivity, PaperRecord
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


@pytest.mark.django_db
def test_maintainer_rename_updates_shared_context_and_audit(api_client):
    maintainer = UserFactory(global_role="advisor", status="active")
    paper = _paper(advisor=maintainer, title="Legacy Shared Title")

    response = authenticate(api_client, maintainer).patch(
        f"/api/library/papers/{paper.id}/",
        {"newTitle": "Maintainer Renamed Title", "reason": "Better title"},
        format="json",
    )

    paper.refresh_from_db()
    activity = PaperLibraryActivity.objects.get(
        paper=paper,
        action=PaperLibraryActivity.Action.PAPER_RENAMED,
    )

    assert response.status_code == 200
    assert response.data["canonicalTitle"] == "Maintainer Renamed Title"
    assert paper.title == "Maintainer Renamed Title"
    assert paper.canonical_title == "Maintainer Renamed Title"
    assert activity.actor == maintainer
    assert activity.outcome == PaperLibraryActivity.Outcome.SUCCESS
    assert activity.reason == "Better title"


@pytest.mark.django_db
def test_non_maintainer_rename_is_denied_and_does_not_change_title(api_client):
    advisor = UserFactory(global_role="advisor", status="active")
    student = UserFactory(global_role="student", status="active")
    paper = _paper(advisor=advisor, title="Protected Shared Title")

    response = authenticate(api_client, student).patch(
        f"/api/library/papers/{paper.id}/",
        {"newTitle": "Student Edited Title"},
        format="json",
    )

    paper.refresh_from_db()

    assert response.status_code == 403
    assert paper.canonical_title == "Protected Shared Title"
    assert not PaperLibraryActivity.objects.filter(
        paper=paper,
        action=PaperLibraryActivity.Action.PAPER_RENAMED,
    ).exists()


@pytest.mark.django_db
def test_maintainer_delete_excludes_paper_from_shared_list_detail_download_and_audits(api_client):
    maintainer = UserFactory(global_role="advisor", status="active")
    student = UserFactory(global_role="student", status="active")
    paper = _paper(advisor=maintainer, title="Deletable Shared Paper")
    maintainer_client = authenticate(api_client, maintainer)

    delete_response = maintainer_client.delete(
        f"/api/library/papers/{paper.id}/",
        {"reason": "Incorrect upload"},
        format="json",
    )
    list_response = authenticate(api_client, student).get("/api/library/papers/?q=Deletable")
    detail_response = authenticate(api_client, student).get(f"/api/library/papers/{paper.id}/")
    download_response = authenticate(api_client, student).get(
        f"/api/library/papers/{paper.id}/download/"
    )
    paper.refresh_from_db()
    activity = PaperLibraryActivity.objects.get(
        paper=paper,
        action=PaperLibraryActivity.Action.PAPER_DELETED,
    )

    assert delete_response.status_code == 204
    assert paper.status == PaperRecord.Status.DELETED
    assert list_response.status_code == 200
    assert list_response.data["results"] == []
    assert detail_response.status_code == 404
    assert download_response.status_code == 404
    assert activity.actor == maintainer
    assert activity.outcome == PaperLibraryActivity.Outcome.SUCCESS
    assert activity.reason == "Incorrect upload"


@pytest.mark.django_db
def test_non_maintainer_delete_is_denied_and_keeps_paper_available(api_client):
    advisor = UserFactory(global_role="advisor", status="active")
    student = UserFactory(global_role="student", status="active")
    paper = _paper(advisor=advisor, title="Protected Delete Paper")

    response = authenticate(api_client, student).delete(
        f"/api/library/papers/{paper.id}/",
        {"reason": "No permission"},
        format="json",
    )
    list_response = authenticate(api_client, student).get("/api/library/papers/?q=Protected")
    paper.refresh_from_db()

    assert response.status_code == 403
    assert paper.status == PaperRecord.Status.ACTIVE
    assert [item["id"] for item in list_response.data["results"]] == [paper.id]
