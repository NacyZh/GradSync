import pytest

from apps.library.models import PaperLibraryActivity, PaperRecord
from apps.projects.models import ResearchProject
from tests.factories.accounts import UserFactory
from tests.factories.collaboration import UploadedFileFactory
from tests.helpers import authenticate


@pytest.mark.django_db
def test_shared_paper_download_uses_canonical_title_and_records_activity(api_client):
    advisor = UserFactory(global_role="advisor", status="active")
    downloader = UserFactory(global_role="student", status="active")
    project = ResearchProject.objects.create(title="Private Source Project", advisor=advisor)
    uploaded_file = UploadedFileFactory(
        owner=advisor,
        original_filename="downloaded-local-name.pdf",
        checksum_sha256="c" * 64,
    )
    paper = PaperRecord.objects.create(
        project=project,
        title="Bad Local Name",
        canonical_title="Graph Neural Methods: A Survey",
        normalized_title="graph neural methods a survey",
        title_source="embedded_metadata",
        title_confidence="high",
        authors=["Lin Chen"],
        uploaded_file=uploaded_file,
        checksum_sha256=uploaded_file.checksum_sha256,
        created_by=advisor,
        status=PaperRecord.Status.ACTIVE,
    )

    response = authenticate(api_client, downloader).get(
        f"/api/library/papers/{paper.id}/download/",
        HTTP_X_REQUEST_ID="request-123",
    )

    assert response.status_code == 200
    assert response.data["filename"] == "Graph Neural Methods A Survey.pdf"
    assert response.data["deliveryMode"] == "direct_response"
    assert PaperLibraryActivity.objects.filter(
        actor=downloader,
        paper=paper,
        action=PaperLibraryActivity.Action.DOWNLOAD_STARTED,
        outcome=PaperLibraryActivity.Outcome.SUCCESS,
        request_id="request-123",
    ).exists()


@pytest.mark.django_db
def test_shared_paper_download_denies_inactive_accounts(api_client):
    advisor = UserFactory(global_role="advisor", status="active")
    inactive_user = UserFactory(global_role="student", status="suspended")
    project = ResearchProject.objects.create(title="Shared Download", advisor=advisor)
    uploaded_file = UploadedFileFactory(owner=advisor)
    paper = PaperRecord.objects.create(
        project=project,
        title="Shared Paper",
        canonical_title="Shared Paper",
        normalized_title="shared paper",
        title_source="legacy",
        title_confidence="high",
        authors=["Ada"],
        uploaded_file=uploaded_file,
        checksum_sha256=uploaded_file.checksum_sha256,
        created_by=advisor,
    )

    response = authenticate(api_client, inactive_user).get(
        f"/api/library/papers/{paper.id}/download/"
    )

    assert response.status_code == 403
