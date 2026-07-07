import pytest
from django.core.files.base import ContentFile
from django.core.files.storage import default_storage

from apps.library.models import PaperLibraryActivity, PaperRecord
from apps.projects.models import ResearchProject
from tests.factories.accounts import UserFactory
from tests.factories.collaboration import UploadedFileFactory
from tests.helpers import authenticate


@pytest.mark.django_db
def test_shared_paper_download_uses_canonical_title_and_records_activity(api_client, tmp_path, settings):
    settings.MEDIA_ROOT = tmp_path
    advisor = UserFactory(global_role="advisor", status="active")
    downloader = UserFactory(global_role="student", status="active")
    project = ResearchProject.objects.create(title="Private Source Project", advisor=advisor)
    storage_key = "integration/papers/graph-survey.pdf"
    pdf_bytes = b"%PDF-1.4\nshared-download\n%%EOF"
    default_storage.save(storage_key, ContentFile(pdf_bytes))
    uploaded_file = UploadedFileFactory(
        owner=advisor,
        original_filename="downloaded-local-name.pdf",
        stored_name=storage_key,
        size_bytes=len(pdf_bytes),
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
    assert response.headers["Content-Type"] == "application/pdf"
    assert response.headers["Content-Disposition"] == (
        'attachment; filename="Graph Neural Methods A Survey.pdf"'
    )
    assert b"".join(response.streaming_content) == pdf_bytes
    assert PaperLibraryActivity.objects.filter(
        actor=downloader,
        paper=paper,
        action=PaperLibraryActivity.Action.DOWNLOAD_STARTED,
        outcome=PaperLibraryActivity.Outcome.SUCCESS,
        request_id="request-123",
    ).exists()


@pytest.mark.django_db
def test_shared_paper_download_returns_recoverable_error_for_missing_file(api_client):
    advisor = UserFactory(global_role="advisor", status="active")
    downloader = UserFactory(global_role="student", status="active")
    project = ResearchProject.objects.create(title="Missing Download", advisor=advisor)
    uploaded_file = UploadedFileFactory(
        owner=advisor,
        original_filename="missing.pdf",
        stored_name="integration/papers/missing.pdf",
        checksum_sha256="d" * 64,
    )
    paper = PaperRecord.objects.create(
        project=project,
        title="Missing File Paper",
        canonical_title="Missing File Paper",
        normalized_title="missing file paper",
        title_source="legacy",
        title_confidence="high",
        authors=["Ada"],
        uploaded_file=uploaded_file,
        checksum_sha256=uploaded_file.checksum_sha256,
        created_by=advisor,
        status=PaperRecord.Status.ACTIVE,
    )

    response = authenticate(api_client, downloader).get(
        f"/api/library/papers/{paper.id}/download/",
        HTTP_X_REQUEST_ID="missing-file",
    )

    assert response.status_code == 410
    assert response.data["message"] == "The paper file is no longer available."
    assert PaperLibraryActivity.objects.filter(
        actor=downloader,
        paper=paper,
        action=PaperLibraryActivity.Action.DOWNLOAD_FAILED,
        outcome=PaperLibraryActivity.Outcome.FAILED,
        request_id="missing-file",
    ).exists()


@pytest.mark.django_db
def test_shared_paper_download_returns_recoverable_error_for_deleted_paper(api_client):
    downloader = UserFactory(global_role="student", status="active")
    paper = PaperRecord.objects.create(
        project=ResearchProject.objects.create(
            title="Deleted Download",
            advisor=UserFactory(global_role="advisor", status="active"),
        ),
        title="Deleted Paper",
        canonical_title="Deleted Paper",
        normalized_title="deleted paper",
        title_source="legacy",
        title_confidence="high",
        authors=["Ada"],
        created_by=UserFactory(global_role="advisor", status="active"),
        status=PaperRecord.Status.DELETED,
    )

    response = authenticate(api_client, downloader).get(
        f"/api/library/papers/{paper.id}/download/",
        HTTP_X_REQUEST_ID="deleted-paper",
    )

    assert response.status_code == 410
    assert response.data["message"] == "This paper is no longer available."
    assert PaperLibraryActivity.objects.filter(
        actor=downloader,
        paper=paper,
        action=PaperLibraryActivity.Action.UNAVAILABLE_ACCESS,
        outcome=PaperLibraryActivity.Outcome.REJECTED,
        request_id="deleted-paper",
    ).exists()


@pytest.mark.django_db
def test_shared_paper_download_requires_authenticated_session(api_client):
    paper = PaperRecord.objects.create(
        project=ResearchProject.objects.create(
            title="Session Download",
            advisor=UserFactory(global_role="advisor", status="active"),
        ),
        title="Session Paper",
        canonical_title="Session Paper",
        normalized_title="session paper",
        title_source="legacy",
        title_confidence="high",
        authors=["Ada"],
        created_by=UserFactory(global_role="advisor", status="active"),
    )

    response = api_client.get(f"/api/library/papers/{paper.id}/download/")

    assert response.status_code in {401, 403}


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
