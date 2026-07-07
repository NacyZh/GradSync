import pytest
from django.core.exceptions import PermissionDenied

from apps.library.models import (
    DuplicateDetectionResult,
    PaperFile,
    PaperImportJob,
    PaperLibraryActivity,
    PaperRecord,
    PaperTitleExtractionResult,
)
from apps.library.services import (
    PaperDownloadUnavailable,
    canonical_paper_download_filename,
    delete_shared_paper,
    ensure_active_research_group_user,
    ensure_library_maintainer,
    is_library_maintainer,
    paper_download_response_metadata,
    prepare_shared_paper_download,
    record_paper_library_activity,
    rename_shared_paper,
    same_title_is_distinguishable,
)
from apps.projects.models import ResearchProject
from tests.factories.accounts import UserFactory
from tests.factories.collaboration import PaperRecordFactory


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


@pytest.mark.django_db
def test_paper_library_maintainer_detection_requires_active_advisor_or_admin():
    advisor = UserFactory(global_role="advisor", status="active")
    admin = UserFactory(global_role="admin", status="active")
    student = UserFactory(global_role="student", status="active")
    suspended_advisor = UserFactory(global_role="advisor", status="suspended")

    assert is_library_maintainer(advisor) is True
    assert is_library_maintainer(admin) is True
    assert is_library_maintainer(student) is False
    assert is_library_maintainer(suspended_advisor) is False

    ensure_library_maintainer(advisor)
    with pytest.raises(PermissionDenied, match="maintainer"):
        ensure_library_maintainer(student)
    with pytest.raises(PermissionDenied, match="Active account"):
        ensure_active_research_group_user(suspended_advisor)


@pytest.mark.django_db
def test_title_based_download_metadata_uses_safe_pdf_attachment_filename():
    paper = PaperRecordFactory(
        title="Ignored original title",
        canonical_title='Graph: "Neural"/Methods? 2026',
    )

    assert canonical_paper_download_filename(paper) == "Graph Neural Methods 2026.pdf"

    metadata = paper_download_response_metadata(paper)

    assert metadata["filename"] == "Graph Neural Methods 2026.pdf"
    assert metadata["contentType"] == "application/pdf"
    assert metadata["contentDisposition"] == 'attachment; filename="Graph Neural Methods 2026.pdf"'


@pytest.mark.django_db
def test_prepare_shared_paper_download_denies_deleted_paper_and_records_unavailable_access():
    user = UserFactory(global_role="student", status="active")
    paper = PaperRecordFactory(
        status=PaperRecord.Status.DELETED,
        title="Deleted Download",
        canonical_title="Deleted Download",
    )

    with pytest.raises(PaperDownloadUnavailable, match="no longer available"):
        prepare_shared_paper_download(user=user, paper=paper, request_id="stale-delete")

    activity = PaperLibraryActivity.objects.get(
        actor=user,
        paper=paper,
        action=PaperLibraryActivity.Action.UNAVAILABLE_ACCESS,
    )
    assert activity.outcome == PaperLibraryActivity.Outcome.REJECTED
    assert activity.request_id == "stale-delete"


@pytest.mark.django_db
def test_same_title_rename_requires_author_or_year_distinction():
    existing = PaperRecordFactory(
        title="Shared Graph Paper",
        canonical_title="Shared Graph Paper",
        normalized_title="shared graph paper",
        authors=["Ada Lovelace"],
        publication_year=2026,
    )
    PaperRecordFactory(
        title="Other Paper",
        canonical_title="Other Paper",
        normalized_title="other paper",
        authors=["Grace Hopper"],
        publication_year=2026,
        project=existing.project,
    )
    queryset = PaperRecord.objects.exclude(pk=existing.pk)

    assert (
        same_title_is_distinguishable(
            title="Other Paper",
            authors=["Grace Hopper"],
            publication_year=2026,
            existing_queryset=queryset,
        )
        is False
    )
    assert (
        same_title_is_distinguishable(
            title="Other Paper",
            authors=["Katherine Johnson"],
            publication_year=2026,
            existing_queryset=queryset,
        )
        is True
    )
    assert (
        same_title_is_distinguishable(
            title="Other Paper",
            authors=["Grace Hopper"],
            publication_year=2025,
            existing_queryset=queryset,
        )
        is True
    )


@pytest.mark.django_db
def test_rename_shared_paper_rejects_blank_and_overlength_titles():
    maintainer = UserFactory(global_role="advisor", status="active")
    paper = PaperRecordFactory(created_by=maintainer, project__advisor=maintainer)

    with pytest.raises(ValueError, match="required"):
        rename_shared_paper(actor=maintainer, paper=paper, new_title="   ")

    with pytest.raises(ValueError, match="500"):
        rename_shared_paper(actor=maintainer, paper=paper, new_title="x" * 501)


@pytest.mark.django_db
def test_delete_shared_paper_soft_deletes_without_restore_state():
    maintainer = UserFactory(global_role="advisor", status="active")
    paper = PaperRecordFactory(created_by=maintainer, project__advisor=maintainer)

    deleted = delete_shared_paper(actor=maintainer, paper=paper, reason="Outdated duplicate")

    deleted.refresh_from_db()
    activity = PaperLibraryActivity.objects.get(
        paper=deleted,
        action=PaperLibraryActivity.Action.PAPER_DELETED,
    )

    assert deleted.status == PaperRecord.Status.DELETED
    assert deleted.deleted_by == maintainer
    assert deleted.deleted_at is not None
    assert deleted.delete_reason == "Outdated duplicate"
    assert not hasattr(deleted, "restored_at")
    assert activity.outcome == PaperLibraryActivity.Outcome.SUCCESS


@pytest.mark.django_db
def test_delete_shared_paper_rejects_already_unavailable_papers():
    maintainer = UserFactory(global_role="advisor", status="active")
    paper = PaperRecordFactory(
        status=PaperRecord.Status.DELETED,
        created_by=maintainer,
        project__advisor=maintainer,
    )

    with pytest.raises(ValueError, match="already unavailable"):
        delete_shared_paper(actor=maintainer, paper=paper)
