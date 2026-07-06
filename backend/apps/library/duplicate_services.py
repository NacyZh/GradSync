import re
from dataclasses import dataclass
from difflib import SequenceMatcher

from django.conf import settings
from django.core.exceptions import PermissionDenied, ValidationError
from django.db import transaction
from django.utils import timezone

from .models import (
    DuplicateDetectionResult,
    PaperAttachment,
    PaperFile,
    PaperImportJob,
    PaperLibraryActivity,
    PaperRecord,
)
from .services import record_paper_library_activity


@dataclass(frozen=True)
class DuplicateMatch:
    paper: PaperRecord
    reason: str


@dataclass(frozen=True)
class SharedDuplicateDecision:
    decision: str
    match_basis: str
    candidate_paper: PaperRecord | None = None
    similarity_score: float | None = None


def normalize_doi(value: str | None) -> str:
    normalized = (value or "").strip().lower()
    normalized = re.sub(r"^https?://(dx\.)?doi\.org/", "", normalized)
    normalized = re.sub(r"^doi:\s*", "", normalized)
    return normalized


def normalize_external_ids(value: dict | None) -> dict[str, str]:
    return {str(k).lower(): str(v).strip().lower() for k, v in (value or {}).items() if v}


def normalize_title(value: str | None) -> str:
    return re.sub(r"\s+", " ", re.sub(r"[^a-z0-9\s]", " ", (value or "").lower())).strip()


def title_author_year_fingerprint(
    *, title: str | None, authors: list[str] | None, publication_year: int | None
) -> str:
    first_author = ""
    if authors:
        first_author = normalize_title(authors[0])
    return f"{normalize_title(title)}|{first_author}|{publication_year or ''}"


def _normalized_people(values: list[str] | None) -> set[str]:
    people = set()
    for value in values or []:
        normalized = normalize_title(value)
        if normalized:
            people.add(normalized)
    return people


def _has_author_overlap(candidate: PaperRecord, authors: list[str] | None) -> bool:
    incoming = _normalized_people(authors)
    existing = _normalized_people(candidate.authors if isinstance(candidate.authors, list) else [])
    return bool(incoming and existing and incoming.intersection(existing))


def detect_shared_paper_duplicate(
    *,
    file_fingerprint: str,
    normalized_title: str,
    authors: list[str] | None = None,
    publication_year: int | None = None,
) -> SharedDuplicateDecision:
    fingerprint_match = (
        PaperFile.objects.select_related("paper")
        .filter(
            file_fingerprint=file_fingerprint,
            paper__status=PaperRecord.Status.ACTIVE,
        )
        .first()
    )
    if fingerprint_match and fingerprint_match.paper_id:
        return SharedDuplicateDecision(
            decision=DuplicateDetectionResult.Decision.DUPLICATE_FILE_FINGERPRINT,
            match_basis=DuplicateDetectionResult.MatchBasis.FILE_FINGERPRINT,
            candidate_paper=fingerprint_match.paper,
            similarity_score=1.0,
        )

    normalized_title = normalize_title(normalized_title)
    active_papers = PaperRecord.objects.filter(status=PaperRecord.Status.ACTIVE).exclude(
        normalized_title=""
    )
    exact_title_matches = active_papers.filter(normalized_title=normalized_title)
    for paper in exact_title_matches:
        year_matches = bool(publication_year and paper.publication_year == publication_year)
        if _has_author_overlap(paper, authors) or year_matches:
            return SharedDuplicateDecision(
                decision=DuplicateDetectionResult.Decision.DUPLICATE_METADATA_STRONG_MATCH,
                match_basis=DuplicateDetectionResult.MatchBasis.NORMALIZED_TITLE_AUTHOR_YEAR,
                candidate_paper=paper,
                similarity_score=1.0,
            )

    fuzzy_threshold = float(
        getattr(settings, "PAPER_LIBRARY_DUPLICATE_FUZZY_MATCH_THRESHOLD", 0.82)
    )
    best_paper = None
    best_score = 0.0
    if normalized_title:
        for paper in active_papers.only("id", "normalized_title", "title", "canonical_title"):
            score = SequenceMatcher(None, normalized_title, paper.normalized_title or "").ratio()
            if score > best_score:
                best_score = score
                best_paper = paper
    if best_paper and best_score >= fuzzy_threshold:
        return SharedDuplicateDecision(
            decision=DuplicateDetectionResult.Decision.MAINTAINER_REVIEW,
            match_basis=DuplicateDetectionResult.MatchBasis.FUZZY_TITLE_METADATA,
            candidate_paper=best_paper,
            similarity_score=best_score,
        )

    return SharedDuplicateDecision(
        decision=DuplicateDetectionResult.Decision.ACCEPTED_NEW,
        match_basis=DuplicateDetectionResult.MatchBasis.NONE,
    )


def create_duplicate_detection_result(
    *,
    paper_file: PaperFile,
    decision: SharedDuplicateDecision,
    authors: list[str] | None,
    publication_year: int | None,
) -> DuplicateDetectionResult:
    candidate = decision.candidate_paper
    return DuplicateDetectionResult.objects.create(
        paper_file=paper_file,
        candidate_paper=candidate,
        decision=decision.decision,
        match_basis=decision.match_basis,
        matched_title=candidate.canonical_title or candidate.title if candidate else "",
        matched_authors=candidate.authors if candidate else authors or [],
        matched_year=candidate.publication_year if candidate else publication_year,
        similarity_score=decision.similarity_score,
        review_status=DuplicateDetectionResult.ReviewStatus.PENDING
        if decision.decision == DuplicateDetectionResult.Decision.MAINTAINER_REVIEW
        else DuplicateDetectionResult.ReviewStatus.NONE,
    )


def _is_maintainer(user) -> bool:
    return bool(getattr(user, "is_administrator", False) or getattr(user, "is_advisor", False))


@transaction.atomic
def review_paper_import(
    *,
    import_job: PaperImportJob,
    reviewer,
    decision: str,
    note: str = "",
) -> PaperImportJob:
    if not _is_maintainer(reviewer):
        raise PermissionDenied("Only maintainers can review paper imports.")
    if import_job.status != PaperImportJob.Status.MAINTAINER_REVIEW:
        raise ValidationError("Only imports awaiting maintainer review can be reviewed.")
    if decision not in {"confirm_duplicate", "confirm_distinct"}:
        raise ValidationError("Unsupported paper import review decision.")
    if not import_job.paper_file_id:
        raise ValidationError("Import has no paper file to review.")

    duplicate_result = import_job.paper_file.duplicate_detection_results.first()
    if duplicate_result is None:
        raise ValidationError("Import has no duplicate detection result.")

    now = timezone.now()
    if decision == "confirm_duplicate":
        duplicate_result.review_status = DuplicateDetectionResult.ReviewStatus.CONFIRMED_DUPLICATE
        duplicate_result.reviewed_by = reviewer
        duplicate_result.reviewed_at = now
        duplicate_result.save(update_fields=["review_status", "reviewed_by", "reviewed_at"])
        import_job.status = PaperImportJob.Status.DUPLICATE
        import_job.duplicate_paper = duplicate_result.candidate_paper
        import_job.failure_reason = PaperImportJob.FailureReason.DUPLICATE
        import_job.user_message = "Maintainer confirmed this upload duplicates an existing paper."
        import_job.completed_at = now
        import_job.save(
            update_fields=[
                "status",
                "duplicate_paper",
                "failure_reason",
                "user_message",
                "completed_at",
                "updated_at",
            ]
        )
        record_paper_library_activity(
            actor=reviewer,
            paper=duplicate_result.candidate_paper,
            paper_file=import_job.paper_file,
            import_job=import_job,
            action=PaperLibraryActivity.Action.DUPLICATE_REJECTED,
            outcome=PaperLibraryActivity.Outcome.REJECTED,
            reason=note or "confirmed_duplicate",
        )
        return import_job

    from .import_services import create_accepted_paper_from_import

    paper = create_accepted_paper_from_import(import_job=import_job)
    duplicate_result.review_status = DuplicateDetectionResult.ReviewStatus.CONFIRMED_DISTINCT
    duplicate_result.reviewed_by = reviewer
    duplicate_result.reviewed_at = now
    duplicate_result.save(update_fields=["review_status", "reviewed_by", "reviewed_at"])
    import_job.status = PaperImportJob.Status.ACCEPTED
    import_job.accepted_paper = paper
    import_job.failure_reason = ""
    import_job.user_message = "Maintainer confirmed this upload as a distinct paper."
    import_job.completed_at = now
    import_job.save(
        update_fields=[
            "status",
            "accepted_paper",
            "failure_reason",
            "user_message",
            "completed_at",
            "updated_at",
        ]
    )
    record_paper_library_activity(
        actor=reviewer,
        paper=paper,
        paper_file=import_job.paper_file,
        import_job=import_job,
        action=PaperLibraryActivity.Action.UPLOAD_ACCEPTED,
        outcome=PaperLibraryActivity.Outcome.SUCCESS,
        reason=note or "confirmed_distinct",
    )
    return import_job


def find_duplicate(
    project,
    *,
    checksum_sha256: str | None = None,
    doi: str | None = None,
    external_ids: dict | None = None,
    title: str | None = None,
    authors: list[str] | None = None,
    publication_year: int | None = None,
) -> DuplicateMatch | None:
    if checksum_sha256:
        paper = PaperRecord.objects.filter(
            project=project,
            checksum_sha256=checksum_sha256,
            status=PaperRecord.Status.ACTIVE,
        ).first()
        if paper:
            return DuplicateMatch(paper, "checksum")
        attachment = (
            PaperAttachment.objects.select_related("paper")
            .filter(
                project=project,
                checksum_sha256=checksum_sha256,
                status=PaperAttachment.Status.ACTIVE,
                paper__status=PaperRecord.Status.ACTIVE,
            )
            .first()
        )
        if attachment:
            return DuplicateMatch(attachment.paper, "checksum")

    normalized_doi = normalize_doi(doi)
    if normalized_doi:
        paper = PaperRecord.objects.filter(
            project=project, status=PaperRecord.Status.ACTIVE, doi__iexact=normalized_doi
        ).first()
        if paper:
            return DuplicateMatch(paper, "doi")

    normalized_external = normalize_external_ids(external_ids)
    for key, value in normalized_external.items():
        paper = PaperRecord.objects.filter(
            project=project,
            status=PaperRecord.Status.ACTIVE,
            external_ids__has_key=key,
        ).first()
        if paper and normalize_external_ids(paper.external_ids).get(key) == value:
            return DuplicateMatch(paper, "external_id")

    fingerprint = title_author_year_fingerprint(
        title=title, authors=authors, publication_year=publication_year
    )
    if fingerprint.strip("|"):
        paper = PaperRecord.objects.filter(
            project=project, status=PaperRecord.Status.ACTIVE, fingerprint=fingerprint
        ).first()
        if paper:
            return DuplicateMatch(paper, "title_author_year")
    return None
