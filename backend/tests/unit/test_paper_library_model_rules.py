import pytest

from apps.library.models import (
    DuplicateDetectionResult,
    PaperFile,
    PaperImportJob,
    PaperLibraryActivity,
    PaperRecord,
    PaperTitleExtractionResult,
)
from apps.library.services import record_paper_library_activity
from apps.projects.models import ResearchProject
from tests.factories.accounts import UserFactory


@pytest.mark.django_db
def test_paper_record_derives_canonical_and_normalized_titles():
    user = UserFactory(status="active")
    project = ResearchProject.objects.create(title="Papers", advisor=user)

    paper = PaperRecord.objects.create(
        project=project,
        title=" Graph: Neural Methods! ",
        authors=["Ada"],
        created_by=user,
    )

    assert paper.canonical_title == " Graph: Neural Methods! "
    assert paper.normalized_title == "graph neural methods"


@pytest.mark.django_db
def test_paper_workflow_models_store_status_and_activity_without_local_paths():
    user = UserFactory(status="active")
    project = ResearchProject.objects.create(title="Papers", advisor=user)
    paper = PaperRecord.objects.create(
        project=project,
        title="Paper",
        authors=["Ada"],
        created_by=user,
    )
    paper_file = PaperFile.objects.create(
        paper=paper,
        original_filename="local name.pdf",
        default_download_filename="Paper.pdf",
        content_type="application/pdf",
        size_bytes=1024,
        file_fingerprint="f" * 64,
        validation_status=PaperFile.ValidationStatus.VALID,
        uploaded_by=user,
    )
    extraction = PaperTitleExtractionResult.objects.create(
        paper_file=paper_file,
        source_attempted=PaperTitleExtractionResult.SourceAttempted.EMBEDDED_METADATA,
        extracted_title="Paper",
        normalized_title="paper",
        confidence=PaperTitleExtractionResult.Confidence.HIGH,
    )
    duplicate = DuplicateDetectionResult.objects.create(
        paper_file=paper_file,
        candidate_paper=paper,
        decision=DuplicateDetectionResult.Decision.DUPLICATE_FILE_FINGERPRINT,
        match_basis=DuplicateDetectionResult.MatchBasis.FILE_FINGERPRINT,
    )
    job = PaperImportJob.objects.create(
        paper_file=paper_file,
        requested_by=user,
        status=PaperImportJob.Status.DUPLICATE,
        duplicate_paper=paper,
    )
    activity = record_paper_library_activity(
        actor=user,
        paper=paper,
        paper_file=paper_file,
        import_job=job,
        action=PaperLibraryActivity.Action.DUPLICATE_REJECTED,
        outcome=PaperLibraryActivity.Outcome.REJECTED,
        reason="/tmp/private/local name.pdf",
    )

    assert extraction.source_attempted == "embedded_metadata"
    assert duplicate.review_status == DuplicateDetectionResult.ReviewStatus.NONE
    assert job.status == PaperImportJob.Status.DUPLICATE
    assert activity.reason == "local name.pdf"
