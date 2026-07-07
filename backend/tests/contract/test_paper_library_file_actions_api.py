import pytest

from apps.library.models import PaperRecord
from tests.factories.accounts import UserFactory
from tests.factories.collaboration import PaperRecordFactory
from tests.helpers import authenticate


pytestmark = pytest.mark.django_db


def test_shared_paper_detail_returns_viewer_capabilities(api_client):
    user = UserFactory(global_role="student", status="active")
    paper = PaperRecordFactory(title="Viewer Contract Paper", canonical_title="Viewer Contract Paper")

    response = authenticate(api_client, user).get(f"/api/library/papers/{paper.id}/")

    assert response.status_code == 200
    assert response.data["id"] == paper.id
    assert response.data["canonicalTitle"] == "Viewer Contract Paper"
    assert response.data["viewerAvailable"] is True
    assert response.data["actionCapabilities"]["canView"] is True
    assert response.data["actionCapabilities"]["canDownload"] is True


def test_shared_paper_detail_excludes_deleted_and_invalid_papers(api_client):
    user = UserFactory(global_role="student", status="active")
    deleted = PaperRecordFactory(status=PaperRecord.Status.DELETED)
    invalid = PaperRecordFactory(status=PaperRecord.Status.INVALID)
    client = authenticate(api_client, user)

    deleted_response = client.get(f"/api/library/papers/{deleted.id}/")
    invalid_response = client.get(f"/api/library/papers/{invalid.id}/")

    assert deleted_response.status_code == 404
    assert invalid_response.status_code == 404


def test_maintainer_can_rename_shared_paper(api_client):
    maintainer = UserFactory(global_role="advisor", status="active")
    paper = PaperRecordFactory(
        title="Original Contract Title",
        canonical_title="Original Contract Title",
        normalized_title="original contract title",
        created_by=maintainer,
        project__advisor=maintainer,
    )

    response = authenticate(api_client, maintainer).patch(
        f"/api/library/papers/{paper.id}/",
        {"newTitle": "Renamed Contract Title", "reason": "Clearer library title"},
        format="json",
    )

    assert response.status_code == 200
    assert response.data["title"] == "Renamed Contract Title"
    assert response.data["canonicalTitle"] == "Renamed Contract Title"
    assert response.data["defaultDownloadFilename"] == "Renamed Contract Title.pdf"


def test_non_maintainer_cannot_rename_shared_paper(api_client):
    user = UserFactory(global_role="student", status="active")
    paper = PaperRecordFactory()

    response = authenticate(api_client, user).patch(
        f"/api/library/papers/{paper.id}/",
        {"newTitle": "Student Rename"},
        format="json",
    )

    assert response.status_code == 403


def test_rename_rejects_invalid_payload(api_client):
    maintainer = UserFactory(global_role="advisor", status="active")
    paper = PaperRecordFactory(created_by=maintainer, project__advisor=maintainer)

    response = authenticate(api_client, maintainer).patch(
        f"/api/library/papers/{paper.id}/",
        {"newTitle": ""},
        format="json",
    )

    assert response.status_code == 400


def test_rename_rejects_indistinguishable_same_title(api_client):
    maintainer = UserFactory(global_role="advisor", status="active")
    project = PaperRecordFactory(created_by=maintainer, project__advisor=maintainer).project
    paper = PaperRecordFactory(
        title="Rename Candidate",
        canonical_title="Rename Candidate",
        normalized_title="rename candidate",
        authors=["Ada Lovelace"],
        publication_year=2026,
        project=project,
        created_by=maintainer,
    )
    PaperRecordFactory(
        title="Existing Graph Paper",
        canonical_title="Existing Graph Paper",
        normalized_title="existing graph paper",
        authors=["Ada Lovelace"],
        publication_year=2026,
        project=project,
        created_by=maintainer,
    )

    response = authenticate(api_client, maintainer).patch(
        f"/api/library/papers/{paper.id}/",
        {"newTitle": "Existing Graph Paper"},
        format="json",
    )

    assert response.status_code == 409


def test_maintainer_can_delete_shared_paper(api_client):
    maintainer = UserFactory(global_role="advisor", status="active")
    paper = PaperRecordFactory(
        title="Delete Contract Paper",
        canonical_title="Delete Contract Paper",
        created_by=maintainer,
        project__advisor=maintainer,
    )

    response = authenticate(api_client, maintainer).delete(
        f"/api/library/papers/{paper.id}/",
        {"reason": "Remove stale paper"},
        format="json",
    )

    paper.refresh_from_db()

    assert response.status_code == 204
    assert paper.status == PaperRecord.Status.DELETED
    assert paper.deleted_by == maintainer
    assert paper.delete_reason == "Remove stale paper"


def test_non_maintainer_cannot_delete_shared_paper(api_client):
    user = UserFactory(global_role="student", status="active")
    paper = PaperRecordFactory()

    response = authenticate(api_client, user).delete(
        f"/api/library/papers/{paper.id}/",
        {"reason": "Student delete"},
        format="json",
    )

    paper.refresh_from_db()

    assert response.status_code == 403
    assert paper.status == PaperRecord.Status.ACTIVE


def test_delete_missing_or_unavailable_paper_returns_not_found_or_conflict(api_client):
    maintainer = UserFactory(global_role="advisor", status="active")
    deleted = PaperRecordFactory(
        status=PaperRecord.Status.DELETED,
        created_by=maintainer,
        project__advisor=maintainer,
    )
    client = authenticate(api_client, maintainer)

    deleted_response = client.delete(f"/api/library/papers/{deleted.id}/", {}, format="json")
    missing_response = client.delete("/api/library/papers/999999/", {}, format="json")

    assert deleted_response.status_code == 409
    assert missing_response.status_code == 404
