import pytest

from apps.library import services as library_services
from apps.library.models import DuplicateDetectionResult, PaperAttachment, PaperFile, PaperRecord
from apps.library.services.duplicates import (
    detect_shared_paper_duplicate,
    find_duplicate,
    normalize_doi,
    title_author_year_fingerprint,
)
from apps.projects.models import ProjectMembership, ResearchProject
from tests.factories.accounts import UserFactory
from tests.factories.collaboration import UploadedFileFactory


@pytest.mark.django_db
def test_paper_duplicate_precedence_checksum_then_doi_then_title_author_year():
    user = UserFactory()
    project = ResearchProject.objects.create(title="Project", advisor=user)
    ProjectMembership.objects.create(project=project, user=user, role="student")
    checksum_paper = PaperRecord.objects.create(
        project=project,
        title="Checksum Paper",
        authors=["A"],
        publication_year=2025,
        doi="10.1/checksum",
        fingerprint=title_author_year_fingerprint(
            title="Checksum Paper", authors=["A"], publication_year=2025
        ),
        created_by=user,
    )
    PaperAttachment.objects.create(
        paper=checksum_paper,
        project=project,
        storage_key="p.pdf",
        filename="p.pdf",
        checksum_sha256="d" * 64,
        imported_by=user,
    )
    doi_paper = PaperRecord.objects.create(
        project=project,
        title="DOI Paper",
        authors=["B"],
        publication_year=2026,
        doi="10.1/doi",
        fingerprint=title_author_year_fingerprint(
            title="DOI Paper", authors=["B"], publication_year=2026
        ),
        created_by=user,
    )

    match = find_duplicate(
        project,
        checksum_sha256="d" * 64,
        doi="10.1/doi",
        title="DOI Paper",
        authors=["B"],
        publication_year=2026,
    )
    assert match.paper == checksum_paper
    assert match.reason == "checksum"

    match = find_duplicate(project, doi="https://doi.org/10.1/doi")
    assert match.paper == doi_paper
    assert match.reason == "doi"

    match = find_duplicate(project, title="DOI Paper", authors=["B"], publication_year=2026)
    assert match.paper == doi_paper
    assert match.reason == "title_author_year"


def test_doi_and_fingerprint_normalization():
    assert normalize_doi("https://doi.org/10.1000/ABC") == "10.1000/abc"
    assert (
        title_author_year_fingerprint(
            title=" Graph: Neural Methods! ", authors=["Lin, Chen"], publication_year=2026
        )
        == "graph neural methods|lin chen|2026"
    )


@pytest.mark.django_db
def test_shared_duplicate_detection_fingerprint_precedes_metadata_matches():
    user = UserFactory(status="active")
    project = ResearchProject.objects.create(title="Shared", advisor=user)
    uploaded_file = UploadedFileFactory(owner=user, checksum_sha256="a" * 64)
    paper = PaperRecord.objects.create(
        project=project,
        title="Existing Paper",
        canonical_title="Existing Paper",
        normalized_title="existing paper",
        authors=["Ada Lovelace"],
        uploaded_file=uploaded_file,
        checksum_sha256=uploaded_file.checksum_sha256,
        created_by=user,
    )
    PaperFile.objects.create(
        paper=paper,
        uploaded_file=uploaded_file,
        original_filename="existing.pdf",
        content_type="application/pdf",
        size_bytes=100,
        file_fingerprint="f" * 64,
        validation_status=PaperFile.ValidationStatus.VALID,
        uploaded_by=user,
    )

    decision = detect_shared_paper_duplicate(
        file_fingerprint="f" * 64,
        normalized_title="different paper",
        authors=["Other"],
        publication_year=None,
    )

    assert decision.decision == DuplicateDetectionResult.Decision.DUPLICATE_FILE_FINGERPRINT
    assert decision.match_basis == DuplicateDetectionResult.MatchBasis.FILE_FINGERPRINT
    assert decision.candidate_paper == paper


@pytest.mark.django_db
def test_shared_duplicate_detection_uses_strong_title_author_year_match():
    user = UserFactory(status="active")
    project = ResearchProject.objects.create(title="Shared", advisor=user)
    paper = PaperRecord.objects.create(
        project=project,
        title="Graph Neural Methods",
        canonical_title="Graph Neural Methods",
        normalized_title="graph neural methods",
        authors=["Ada Lovelace"],
        publication_year=2026,
        created_by=user,
    )

    decision = detect_shared_paper_duplicate(
        file_fingerprint="a" * 64,
        normalized_title="graph neural methods",
        authors=["Ada Lovelace"],
        publication_year=None,
    )

    assert decision.decision == DuplicateDetectionResult.Decision.DUPLICATE_METADATA_STRONG_MATCH
    assert decision.match_basis == DuplicateDetectionResult.MatchBasis.NORMALIZED_TITLE_AUTHOR_YEAR
    assert decision.candidate_paper == paper


@pytest.mark.django_db
def test_shared_duplicate_detection_routes_fuzzy_title_match_to_review():
    user = UserFactory(status="active")
    project = ResearchProject.objects.create(title="Shared", advisor=user)
    paper = PaperRecord.objects.create(
        project=project,
        title="Graph Neural Methods for Research Groups",
        canonical_title="Graph Neural Methods for Research Groups",
        normalized_title="graph neural methods for research groups",
        authors=["Ada Lovelace"],
        created_by=user,
    )

    decision = detect_shared_paper_duplicate(
        file_fingerprint="b" * 64,
        normalized_title="graph neural method for research group",
        authors=[],
        publication_year=None,
    )

    assert decision.decision == DuplicateDetectionResult.Decision.MAINTAINER_REVIEW
    assert decision.match_basis == DuplicateDetectionResult.MatchBasis.FUZZY_TITLE_METADATA
    assert decision.candidate_paper == paper
    assert decision.similarity_score and decision.similarity_score >= 0.82


@pytest.mark.django_db
def test_shared_duplicate_detection_accepts_distinct_paper():
    user = UserFactory(status="active")
    project = ResearchProject.objects.create(title="Shared", advisor=user)
    PaperRecord.objects.create(
        project=project,
        title="Graph Neural Methods",
        canonical_title="Graph Neural Methods",
        normalized_title="graph neural methods",
        authors=["Ada Lovelace"],
        created_by=user,
    )

    decision = detect_shared_paper_duplicate(
        file_fingerprint="c" * 64,
        normalized_title="quantum control systems",
        authors=["Grace Hopper"],
        publication_year=2026,
    )

    assert decision.decision == DuplicateDetectionResult.Decision.ACCEPTED_NEW
    assert decision.match_basis == DuplicateDetectionResult.MatchBasis.NONE
    assert decision.candidate_paper is None


def test_duplicate_services_remain_available_through_library_service_exports():
    assert library_services.detect_shared_paper_duplicate is detect_shared_paper_duplicate
    assert library_services.find_duplicate is find_duplicate
    assert library_services.normalize_doi is normalize_doi
