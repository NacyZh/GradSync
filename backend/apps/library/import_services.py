import hashlib
import re
from dataclasses import dataclass
from pathlib import PurePath

from django.conf import settings
from django.core.exceptions import ValidationError
from django.db import transaction
from django.utils import timezone
from pypdf import PdfReader
from pypdf.errors import PdfReadError

from apps.audit.services import record_event, record_upload
from apps.common.file_services import checksum_sha256, store_uploaded_file
from apps.projects.archive_services import ensure_project_writable
from apps.projects.models import ResearchProject

from .duplicate_services import (
    create_duplicate_detection_result,
    detect_shared_paper_duplicate,
    find_duplicate,
    normalize_doi,
    normalize_title,
    title_author_year_fingerprint,
)
from .models import (
    DuplicateDetectionResult,
    PaperFile,
    PaperImportBatch,
    PaperImportJob,
    PaperLibraryActivity,
    PaperRecord,
    PaperTitleExtractionResult,
)
from .services import (
    canonical_paper_download_filename,
    ensure_active_research_group_user,
    record_paper_library_activity,
)


class PaperImportError(Exception):
    def __init__(self, reason: str, message: str):
        super().__init__(message)
        self.reason = reason
        self.message = message


@dataclass(frozen=True)
class ValidatedPdfUpload:
    filename: str
    content_type: str
    size_bytes: int
    file_fingerprint: str


@dataclass(frozen=True)
class ExtractedPaperTitle:
    title: str
    source: str
    confidence: str
    authors: list[str]
    publication_year: int | None = None


def _upload_position(upload) -> int | None:
    if hasattr(upload, "tell"):
        try:
            return upload.tell()
        except OSError:
            return None
    return None


def _restore_position(upload, position: int | None) -> None:
    if position is not None and hasattr(upload, "seek"):
        upload.seek(position)


def _fingerprint(upload) -> str:
    digest = hashlib.sha256()
    position = _upload_position(upload)
    for chunk in upload.chunks():
        digest.update(chunk)
    _restore_position(upload, position)
    return digest.hexdigest()


def _reader_for(upload) -> PdfReader:
    position = _upload_position(upload)
    try:
        if hasattr(upload, "seek"):
            upload.seek(0)
        reader = PdfReader(upload)
    except (PdfReadError, OSError, ValueError) as exc:
        raise PaperImportError("unreadable_pdf", "PDF could not be read.") from exc
    finally:
        _restore_position(upload, position)
    if reader.is_encrypted:
        raise PaperImportError("password_blocked", "Password-protected PDFs are not supported.")
    return reader


def _reliable_title(value: str | None) -> str:
    title = " ".join(str(value or "").replace("\x00", " ").split()).strip()
    if len(title) < 4 or title.lower() in {"untitled", "unknown", "paper"}:
        return ""
    return title[:500]


def _metadata_authors(value: str | None) -> list[str]:
    raw = " ".join(str(value or "").replace("\x00", " ").split()).strip()
    if not raw:
        return []
    authors = re.split(r"\s*(?:;|,|\band\b)\s*", raw)
    return [author[:160] for author in authors if author.strip()]


def _metadata_year(*values: str | None) -> int | None:
    for value in values:
        match = re.search(r"(19|20)\d{2}", str(value or ""))
        if match:
            return int(match.group(0))
    return None


def validate_pdf_upload(upload) -> ValidatedPdfUpload:
    raw_name = str(getattr(upload, "name", "") or "")
    filename = PurePath(raw_name).name
    if not filename or filename != raw_name or ".." in PurePath(raw_name).parts:
        raise PaperImportError("unsafe_path", "Unsafe local filename is not allowed.")
    if PurePath(filename).suffix.lower() != ".pdf":
        raise PaperImportError("unsupported_type", "Only PDF files can be imported.")

    content_type = str(getattr(upload, "content_type", "") or "")
    if content_type and content_type not in {"application/pdf", "application/octet-stream"}:
        raise PaperImportError("unsupported_type", "Only PDF files can be imported.")

    size_bytes = int(getattr(upload, "size", 0) or 0)
    if size_bytes <= 0:
        raise PaperImportError("empty_file", "The selected PDF is empty.")
    limit = int(getattr(settings, "PAPER_LIBRARY_UPLOAD_LIMIT_BYTES", 0) or 0)
    if limit and size_bytes > limit:
        raise PaperImportError("oversized", "The selected PDF exceeds the upload size limit.")

    try:
        _reader_for(upload)
    except PaperImportError as exc:
        if exc.reason in {"password_blocked", "unreadable_pdf"}:
            reason = "password_blocked" if exc.reason == "password_blocked" else "corrupted_pdf"
            message = (
                "Password-protected PDFs are not supported."
                if reason == "password_blocked"
                else "The selected PDF is corrupted or unreadable."
            )
            raise PaperImportError(reason, message) from exc
        raise

    return ValidatedPdfUpload(
        filename=filename,
        content_type=content_type or "application/pdf",
        size_bytes=size_bytes,
        file_fingerprint=_fingerprint(upload),
    )


def extract_title_from_pdf_upload(upload) -> ExtractedPaperTitle:
    try:
        reader = _reader_for(upload)
    except PaperImportError as exc:
        if exc.reason == "password_blocked":
            raise
        raise PaperImportError("unreadable_pdf", "PDF title could not be extracted.") from exc

    metadata_title = _reliable_title(
        getattr(reader.metadata, "title", "") if reader.metadata else ""
    )
    metadata_author = getattr(reader.metadata, "author", "") if reader.metadata else ""
    metadata_year = _metadata_year(
        getattr(reader.metadata, "creation_date", "") if reader.metadata else "",
        getattr(reader.metadata, "modification_date", "") if reader.metadata else "",
    )
    if metadata_title:
        return ExtractedPaperTitle(
            title=metadata_title,
            source=PaperTitleExtractionResult.SourceAttempted.EMBEDDED_METADATA,
            confidence=PaperTitleExtractionResult.Confidence.HIGH,
            authors=_metadata_authors(metadata_author),
            publication_year=metadata_year,
        )

    first_page_text = ""
    try:
        if reader.pages:
            first_page_text = reader.pages[0].extract_text() or ""
    except (PdfReadError, OSError, ValueError) as exc:
        raise PaperImportError("unreadable_pdf", "PDF first page could not be read.") from exc

    first_line = next((line.strip() for line in first_page_text.splitlines() if line.strip()), "")
    visible_title = _reliable_title(first_line)
    if visible_title:
        return ExtractedPaperTitle(
            title=visible_title,
            source=PaperTitleExtractionResult.SourceAttempted.FIRST_PAGE_VISIBLE_TEXT,
            confidence=PaperTitleExtractionResult.Confidence.MEDIUM,
            authors=_metadata_authors(metadata_author),
            publication_year=metadata_year,
        )
    raise PaperImportError("missing_reliable_title", "No reliable paper title could be extracted.")


def _shared_library_project(user) -> ResearchProject:
    project, _ = ResearchProject.objects.get_or_create(
        title="Shared Paper Library",
        advisor=user,
        defaults={"description": "System project for shared paper-library imports."},
    )
    return project


def _job_failure_reason(reason: str) -> str:
    mapping = {
        "unsupported_type": PaperImportJob.FailureReason.UNSUPPORTED_TYPE,
        "empty_file": PaperImportJob.FailureReason.EMPTY_FILE,
        "corrupted_pdf": PaperImportJob.FailureReason.CORRUPTED_PDF,
        "password_blocked": PaperImportJob.FailureReason.PASSWORD_BLOCKED,
        "oversized": PaperImportJob.FailureReason.OVERSIZED,
        "unsafe_path": PaperImportJob.FailureReason.UNSAFE_PATH,
        "missing_reliable_title": PaperImportJob.FailureReason.MISSING_RELIABLE_TITLE,
        "unreadable_pdf": PaperImportJob.FailureReason.CORRUPTED_PDF,
    }
    return mapping.get(reason, PaperImportJob.FailureReason.UNKNOWN)


def create_accepted_paper_from_import(*, import_job: PaperImportJob) -> PaperRecord:
    paper_file = import_job.paper_file
    if paper_file is None or paper_file.uploaded_file is None:
        raise PaperImportError("processing_error", "Import has no stored PDF file.")
    extraction = paper_file.title_extraction_results.first()
    if extraction is None or not extraction.extracted_title:
        raise PaperImportError(
            "missing_reliable_title",
            "No reliable paper title could be extracted.",
        )

    user = import_job.requested_by
    project = _shared_library_project(user)
    paper = PaperRecord.objects.create(
        project=project,
        title=extraction.extracted_title,
        canonical_title=extraction.extracted_title,
        normalized_title=extraction.normalized_title or normalize_title(extraction.extracted_title),
        title_source=extraction.source_attempted,
        title_confidence=extraction.confidence,
        authors=extraction.extracted_authors,
        publication_year=extraction.extracted_year,
        tags=extraction.extracted_keywords,
        visibility=PaperRecord.Visibility.GROUP_WIDE,
        visibility_changed_by=user,
        visibility_changed_at=timezone.now(),
        uploaded_file=paper_file.uploaded_file,
        checksum_sha256=paper_file.uploaded_file.checksum_sha256,
        import_source=PaperRecord.ImportSource.LOCAL_FILE,
        source_path_label=paper_file.original_filename,
        fingerprint=title_author_year_fingerprint(
            title=extraction.extracted_title,
            authors=extraction.extracted_authors,
            publication_year=extraction.extracted_year,
        ),
        shared_access_started_at=timezone.now(),
        created_by=user,
        status=PaperRecord.Status.ACTIVE,
    )
    paper_file.paper = paper
    paper_file.default_download_filename = canonical_paper_download_filename(paper)
    paper_file.save(update_fields=["paper", "default_download_filename"])
    return paper


@transaction.atomic
def import_shared_paper_pdf(*, user, upload) -> PaperImportJob:
    ensure_active_research_group_user(user)
    validated = validate_pdf_upload(upload)
    uploaded_file = store_uploaded_file(upload=upload, category="paper", owner=user)
    paper_file = PaperFile.objects.create(
        uploaded_file=uploaded_file,
        storage_key=uploaded_file.stored_name,
        original_filename=validated.filename,
        content_type=validated.content_type,
        size_bytes=validated.size_bytes,
        file_fingerprint=validated.file_fingerprint,
        validation_status=PaperFile.ValidationStatus.VALID,
        uploaded_by=user,
    )
    job = PaperImportJob.objects.create(
        paper_file=paper_file,
        requested_by=user,
        status=PaperImportJob.Status.VALIDATING,
        user_message="Validating selected PDF.",
    )

    try:
        job.status = PaperImportJob.Status.EXTRACTING_TITLE
        job.user_message = "Extracting paper title."
        job.save(update_fields=["status", "user_message", "updated_at"])
        extracted = extract_title_from_pdf_upload(upload)
    except PaperImportError as exc:
        PaperTitleExtractionResult.objects.create(
            paper_file=paper_file,
            source_attempted=PaperTitleExtractionResult.SourceAttempted.EMBEDDED_METADATA,
            confidence=PaperTitleExtractionResult.Confidence.FAILED,
            failure_reason=PaperTitleExtractionResult.FailureReason.MISSING_TITLE
            if exc.reason == "missing_reliable_title"
            else PaperTitleExtractionResult.FailureReason.UNREADABLE_PDF,
            completed_at=timezone.now(),
        )
        job.status = PaperImportJob.Status.REJECTED
        job.failure_reason = _job_failure_reason(exc.reason)
        job.user_message = exc.message
        job.completed_at = timezone.now()
        job.save(
            update_fields=[
                "status",
                "failure_reason",
                "user_message",
                "completed_at",
                "updated_at",
            ]
        )
        record_paper_library_activity(
            actor=user,
            paper_file=paper_file,
            import_job=job,
            action=PaperLibraryActivity.Action.UPLOAD_REJECTED,
            outcome=PaperLibraryActivity.Outcome.REJECTED,
            reason=exc.reason,
        )
        return job

    extraction = PaperTitleExtractionResult.objects.create(
        paper_file=paper_file,
        source_attempted=extracted.source,
        extracted_title=extracted.title,
        normalized_title=normalize_title(extracted.title),
        extracted_authors=extracted.authors,
        extracted_year=extracted.publication_year,
        confidence=extracted.confidence,
        completed_at=timezone.now(),
    )
    job.status = PaperImportJob.Status.CHECKING_DUPLICATE
    job.user_message = "Checking for duplicates."
    job.save(update_fields=["status", "user_message", "updated_at"])

    duplicate_decision = detect_shared_paper_duplicate(
        file_fingerprint=validated.file_fingerprint,
        normalized_title=extraction.normalized_title,
        authors=extracted.authors,
        publication_year=extracted.publication_year,
    )
    duplicate_result = create_duplicate_detection_result(
        paper_file=paper_file,
        decision=duplicate_decision,
        authors=extracted.authors,
        publication_year=extracted.publication_year,
    )
    if duplicate_decision.decision in {
        DuplicateDetectionResult.Decision.DUPLICATE_FILE_FINGERPRINT,
        DuplicateDetectionResult.Decision.DUPLICATE_METADATA_STRONG_MATCH,
    }:
        job.status = PaperImportJob.Status.DUPLICATE
        job.user_message = "Duplicate paper detected."
        job.failure_reason = PaperImportJob.FailureReason.DUPLICATE
        job.duplicate_paper = duplicate_decision.candidate_paper
        job.completed_at = timezone.now()
        job.save(
            update_fields=[
                "status",
                "user_message",
                "failure_reason",
                "duplicate_paper",
                "completed_at",
                "updated_at",
            ]
        )
        record_paper_library_activity(
            actor=user,
            paper=duplicate_decision.candidate_paper,
            paper_file=paper_file,
            import_job=job,
            action=PaperLibraryActivity.Action.DUPLICATE_REJECTED,
            outcome=PaperLibraryActivity.Outcome.REJECTED,
            reason=duplicate_decision.decision,
        )
        return job

    if duplicate_decision.decision == DuplicateDetectionResult.Decision.MAINTAINER_REVIEW:
        job.status = PaperImportJob.Status.MAINTAINER_REVIEW
        job.user_message = "Possible duplicate queued for maintainer review."
        job.duplicate_paper = duplicate_result.candidate_paper
        job.save(
            update_fields=[
                "status",
                "user_message",
                "duplicate_paper",
                "updated_at",
            ]
        )
        record_paper_library_activity(
            actor=user,
            paper=duplicate_decision.candidate_paper,
            paper_file=paper_file,
            import_job=job,
            action=PaperLibraryActivity.Action.MAINTAINER_REVIEW_CREATED,
            outcome=PaperLibraryActivity.Outcome.SUCCESS,
            reason=duplicate_decision.match_basis,
        )
        return job

    paper = create_accepted_paper_from_import(import_job=job)
    job.status = PaperImportJob.Status.ACCEPTED
    job.user_message = "Paper imported."
    job.accepted_paper = paper
    job.completed_at = timezone.now()
    job.save(
        update_fields=[
            "status",
            "user_message",
            "accepted_paper",
            "completed_at",
            "updated_at",
        ]
    )
    record_paper_library_activity(
        actor=user,
        paper=paper,
        paper_file=paper_file,
        import_job=job,
        action=PaperLibraryActivity.Action.UPLOAD_ACCEPTED,
        outcome=PaperLibraryActivity.Outcome.SUCCESS,
    )
    return job


def _duplicate_inputs(data: dict) -> dict:
    return {
        "checksum_sha256": data.get("checksum_sha256"),
        "doi": data.get("doi"),
        "external_ids": data.get("external_ids", {}),
        "title": data.get("title"),
        "authors": data.get("authors", []),
        "publication_year": data.get("publication_year"),
    }


def _can_share_group_wide(user) -> bool:
    return bool(
        getattr(user, "is_superuser", False)
        or getattr(user, "is_administrator", False)
        or getattr(user, "is_advisor", False)
    )


class PaperImportService:
    def __init__(self, user, project):
        self.user = user
        self.project = project

    def _require_member(self):
        if not self.project.memberships.filter(user=self.user, status="active").exists():
            raise ValidationError("You are not a member of this project")

    @transaction.atomic
    def create_paper(self, **data) -> PaperRecord:
        self._require_member()
        ensure_project_writable(self.project)
        visibility = data.get("visibility") or PaperRecord.Visibility.PROJECT_MEMBERS
        if visibility == PaperRecord.Visibility.GROUP_WIDE and not _can_share_group_wide(self.user):
            raise PermissionError("Only teachers and administrators can share papers group-wide")
        match = find_duplicate(self.project, **_duplicate_inputs(data))
        if match:
            raise ValidationError(
                {
                    "message": "Duplicate paper detected",
                    "duplicateOfPaperId": str(match.paper.id),
                    "duplicateReason": match.reason,
                }
            )
        paper = PaperRecord.objects.create(
            project=self.project,
            title=data["title"],
            authors=data.get("authors", []),
            venue=data.get("venue", ""),
            publication_year=data.get("publication_year"),
            doi=normalize_doi(data.get("doi")),
            external_ids=data.get("external_ids", {}),
            abstract=data.get("abstract", ""),
            notes=data.get("notes", ""),
            tags=data.get("tags", []),
            visibility=visibility,
            visibility_changed_by=self.user,
            visibility_changed_at=timezone.now(),
            import_source=data.get("import_source", PaperRecord.ImportSource.MANUAL),
            source_path_label=data.get("source_path_label", ""),
            fingerprint=title_author_year_fingerprint(
                title=data.get("title"),
                authors=data.get("authors", []),
                publication_year=data.get("publication_year"),
            ),
            created_by=self.user,
        )
        record_event(self.project, self.user, "paper.created", f"Created paper {paper.id}", paper)
        return paper

    @transaction.atomic
    def upload_paper(self, *, upload, **data) -> PaperRecord:
        self._require_member()
        ensure_project_writable(self.project)
        visibility = data.get("visibility") or PaperRecord.Visibility.PROJECT_MEMBERS
        if visibility == PaperRecord.Visibility.GROUP_WIDE and not _can_share_group_wide(self.user):
            raise PermissionError("Only teachers and administrators can share papers group-wide")

        checksum = checksum_sha256(upload)
        duplicate_inputs = _duplicate_inputs(data)
        duplicate_inputs["checksum_sha256"] = checksum
        match = find_duplicate(self.project, **duplicate_inputs)
        if match:
            raise ValidationError(
                {
                    "message": "Duplicate paper detected",
                    "duplicateOfPaperId": str(match.paper.id),
                    "duplicateReason": match.reason,
                }
            )

        uploaded_file = store_uploaded_file(upload=upload, category="paper", owner=self.user)
        paper = PaperRecord.objects.create(
            project=self.project,
            title=data["title"],
            authors=data.get("authors", []),
            venue=data.get("venue", ""),
            publication_year=data.get("publication_year"),
            doi=normalize_doi(data.get("doi")),
            external_ids=data.get("external_ids", {}),
            abstract=data.get("abstract", ""),
            notes=data.get("notes", ""),
            tags=data.get("tags", []),
            visibility=visibility,
            visibility_changed_by=self.user,
            visibility_changed_at=timezone.now(),
            uploaded_file=uploaded_file,
            checksum_sha256=uploaded_file.checksum_sha256,
            import_source=PaperRecord.ImportSource.LOCAL_FILE,
            source_path_label=uploaded_file.original_filename,
            fingerprint=title_author_year_fingerprint(
                title=data.get("title"),
                authors=data.get("authors", []),
                publication_year=data.get("publication_year"),
            ),
            created_by=self.user,
        )
        record_upload(self.project, self.user, paper, "paper")
        return paper

    @transaction.atomic
    def stage_import(
        self, *, source_type: str, items: list[dict], source_path_label: str = ""
    ) -> PaperImportBatch:
        self._require_member()
        ensure_project_writable(self.project)
        results = []
        accepted_count = duplicate_count = error_count = 0
        for item in items:
            try:
                match = find_duplicate(self.project, **_duplicate_inputs(item))
                if match:
                    duplicate_count += 1
                    results.append(
                        {
                            "status": "duplicate",
                            "duplicateOfPaperId": str(match.paper.id),
                            "duplicateReason": match.reason,
                            "message": "Duplicate paper detected",
                        }
                    )
                else:
                    accepted_count += 1
                    results.append({"status": "accepted", "paper": item})
            except Exception as exc:
                error_count += 1
                results.append({"status": "error", "message": str(exc)})
        batch = PaperImportBatch.objects.create(
            project=self.project,
            requested_by=self.user,
            source_type=source_type,
            source_path_label=source_path_label,
            total_items=len(items),
            accepted_count=accepted_count,
            duplicate_count=duplicate_count,
            error_count=error_count,
            result_summary=results,
        )
        record_event(
            self.project, self.user, "paper_import.staged", f"Staged paper import {batch.id}", batch
        )
        return batch

    @transaction.atomic
    def commit_import(self, batch: PaperImportBatch) -> PaperImportBatch:
        self._require_member()
        ensure_project_writable(self.project)
        for result in batch.result_summary:
            if result.get("status") == "accepted" and isinstance(result.get("paper"), dict):
                paper_data = result["paper"]
                paper = self.create_paper(
                    **{
                        **paper_data,
                        "import_source": PaperRecord.ImportSource.BATCH,
                        "source_path_label": batch.source_path_label,
                    }
                )
                result["paper"] = {"id": str(paper.id), "title": paper.title}
        batch.status = PaperImportBatch.Status.COMMITTED
        batch.committed_at = timezone.now()
        batch.save(update_fields=["status", "committed_at", "result_summary"])
        record_event(
            self.project,
            self.user,
            "paper_import.committed",
            f"Committed paper import {batch.id}",
            batch,
        )
        return batch
