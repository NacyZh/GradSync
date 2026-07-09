from __future__ import annotations

from dataclasses import dataclass

from django.core.exceptions import PermissionDenied, ValidationError
from django.core.files.storage import default_storage
from django.db.models import Q, QuerySet
from django.utils import timezone

from apps.accounts.models import User

from ..models import PaperAttachment, PaperImportJob, PaperLibraryActivity, PaperRecord
from ..upload_policy import shared_paper_upload_policy


class PaperRenameConflict(ValueError):
    pass


class PaperDeleteConflict(ValueError):
    pass


class PaperDownloadUnavailable(RuntimeError):
    pass


@dataclass(frozen=True)
class PreparedSharedPaperDownload:
    storage_key: str
    filename: str
    content_type: str
    content_disposition: str


def is_active_research_group_user(user) -> bool:
    return bool(
        getattr(user, "is_authenticated", False)
        and getattr(user, "status", None) == User.Status.ACTIVE
    )


def ensure_active_research_group_user(user) -> None:
    if not is_active_research_group_user(user):
        raise PermissionDenied("Active account required for the shared paper library.")


def is_library_maintainer(user) -> bool:
    if not is_active_research_group_user(user):
        return False
    return bool(getattr(user, "is_administrator", False) or getattr(user, "is_advisor", False))


def ensure_library_maintainer(user) -> None:
    ensure_active_research_group_user(user)
    if not is_library_maintainer(user):
        raise PermissionDenied("Only paper library maintainers can perform this action.")


def shared_paper_queryset_for(user) -> QuerySet[PaperRecord]:
    ensure_active_research_group_user(user)
    return (
        PaperRecord.objects.filter(status=PaperRecord.Status.ACTIVE)
        .exclude(Q(status=PaperRecord.Status.DELETED) | Q(status=PaperRecord.Status.INVALID))
        .select_related("project", "uploaded_file", "created_by")
        .prefetch_related("attachments")
        .distinct()
    )


def apply_paper_search_filters(queryset: QuerySet[PaperRecord], params) -> QuerySet[PaperRecord]:
    query = params.get("q")
    if query:
        queryset = queryset.filter(
            Q(canonical_title__icontains=query)
            | Q(title__icontains=query)
            | Q(authors__icontains=query)
            | Q(tags__icontains=query)
            | Q(abstract__icontains=query)
            | Q(source_path_label__icontains=query)
        )
    author = params.get("author")
    if author:
        queryset = queryset.filter(authors__icontains=author)
    year = params.get("year")
    if year:
        try:
            year_value = int(year)
        except (TypeError, ValueError):
            return queryset.none()
        queryset = queryset.filter(publication_year=year_value)
    keyword = params.get("keyword") or params.get("tag")
    if keyword:
        queryset = queryset.filter(tags__icontains=keyword)
    return queryset


def canonical_paper_download_filename(paper: PaperRecord) -> str:
    title = paper.canonical_title or paper.title or "paper"
    safe = "".join(char if char.isalnum() or char in " ._-" else " " for char in title)
    safe = " ".join(safe.split()).strip() or "paper"
    return f"{safe}.pdf"


def paper_download_response_metadata(paper: PaperRecord) -> dict:
    filename = canonical_paper_download_filename(paper)
    return {
        "filename": filename,
        "contentType": "application/pdf",
        "contentDisposition": f'attachment; filename="{filename}"',
    }


def format_upload_size_label(size_bytes: int) -> str:
    from apps.common.upload_policy import format_upload_size_label as _format_upload_size_label

    return _format_upload_size_label(size_bytes)


def paper_upload_policy() -> dict:
    return shared_paper_upload_policy()


def same_title_is_distinguishable(
    *,
    title: str,
    authors: list[str] | tuple[str, ...] | None = None,
    publication_year: int | None = None,
    existing_queryset: QuerySet[PaperRecord] | None = None,
) -> bool:
    from .duplicates import normalize_title

    normalized = normalize_title(title)
    if not normalized:
        raise ValidationError("Paper title is required.")
    if existing_queryset is None:
        existing_queryset = PaperRecord.objects.filter(status=PaperRecord.Status.ACTIVE)
    matches = existing_queryset.filter(normalized_title=normalized)
    if not matches.exists():
        return True
    requested_authors = {
        str(author).strip().lower()
        for author in (authors or [])
        if str(author).strip()
    }
    for paper in matches:
        paper_authors = {
            str(author).strip().lower()
            for author in (paper.authors or [])
            if str(author).strip()
        }
        if (
            publication_year
            and paper.publication_year
            and publication_year != paper.publication_year
        ):
            continue
        if requested_authors and paper_authors and requested_authors.isdisjoint(paper_authors):
            continue
        return False
    return True


def rename_shared_paper(
    *,
    actor,
    paper: PaperRecord,
    new_title: str,
    reason: str = "",
    request_id: str = "",
) -> PaperRecord:
    ensure_library_maintainer(actor)
    ensure_paper_available(paper)

    cleaned_title = " ".join(str(new_title or "").split()).strip()
    if not cleaned_title:
        record_paper_library_activity(
            actor=actor,
            paper=paper,
            action=PaperLibraryActivity.Action.PAPER_RENAME_REJECTED,
            outcome=PaperLibraryActivity.Outcome.REJECTED,
            reason="Paper title is required.",
            request_id=request_id,
        )
        raise ValueError("Paper title is required.")
    if len(cleaned_title) > 500:
        record_paper_library_activity(
            actor=actor,
            paper=paper,
            action=PaperLibraryActivity.Action.PAPER_RENAME_REJECTED,
            outcome=PaperLibraryActivity.Outcome.REJECTED,
            reason="Paper title must be 500 characters or fewer.",
            request_id=request_id,
        )
        raise ValueError("Paper title must be 500 characters or fewer.")

    from .duplicates import normalize_title

    normalized_title = normalize_title(cleaned_title)
    same_title_queryset = PaperRecord.objects.filter(
        status=PaperRecord.Status.ACTIVE,
    ).exclude(pk=paper.pk)
    if not same_title_is_distinguishable(
        title=cleaned_title,
        authors=paper.authors or [],
        publication_year=paper.publication_year,
        existing_queryset=same_title_queryset,
    ):
        message = (
            "Another active paper already uses that title without distinguishing "
            "author or year context."
        )
        record_paper_library_activity(
            actor=actor,
            paper=paper,
            action=PaperLibraryActivity.Action.PAPER_RENAME_REJECTED,
            outcome=PaperLibraryActivity.Outcome.REJECTED,
            reason=message,
            request_id=request_id,
        )
        raise PaperRenameConflict(message)

    paper.title = cleaned_title
    paper.canonical_title = cleaned_title
    paper.normalized_title = normalized_title
    paper.save(update_fields=["title", "canonical_title", "normalized_title", "updated_at"])
    record_paper_library_activity(
        actor=actor,
        paper=paper,
        action=PaperLibraryActivity.Action.PAPER_RENAMED,
        outcome=PaperLibraryActivity.Outcome.SUCCESS,
        reason=reason,
        request_id=request_id,
    )
    return paper


def delete_shared_paper(
    *,
    actor,
    paper: PaperRecord,
    reason: str = "",
    request_id: str = "",
) -> PaperRecord:
    ensure_library_maintainer(actor)
    cleaned_reason = " ".join(str(reason or "").split()).strip()
    if paper.status != PaperRecord.Status.ACTIVE:
        message = "Paper is already unavailable."
        record_paper_library_activity(
            actor=actor,
            paper=paper,
            action=PaperLibraryActivity.Action.PAPER_DELETE_REJECTED,
            outcome=PaperLibraryActivity.Outcome.REJECTED,
            reason=message,
            request_id=request_id,
        )
        raise PaperDeleteConflict(message)

    paper.status = PaperRecord.Status.DELETED
    paper.deleted_at = timezone.now()
    paper.deleted_by = actor
    paper.delete_reason = cleaned_reason[:255]
    paper.save(
        update_fields=[
            "status",
            "deleted_at",
            "deleted_by",
            "delete_reason",
            "updated_at",
        ]
    )
    record_paper_library_activity(
        actor=actor,
        paper=paper,
        action=PaperLibraryActivity.Action.PAPER_DELETED,
        outcome=PaperLibraryActivity.Outcome.SUCCESS,
        reason=cleaned_reason,
        request_id=request_id,
    )
    return paper


def ensure_paper_available(paper: PaperRecord) -> None:
    if paper.status != PaperRecord.Status.ACTIVE:
        raise PermissionDenied("Paper is not available in the shared library.")


def _active_paper_storage_metadata(paper: PaperRecord) -> tuple[str, str]:
    if paper.uploaded_file_id:
        return (
            paper.uploaded_file.stored_name,
            paper.uploaded_file.content_type or "application/pdf",
        )
    attachment = paper.attachments.filter(status=PaperAttachment.Status.ACTIVE).first()
    if attachment is not None:
        return attachment.storage_key, attachment.content_type or "application/pdf"
    return "", "application/pdf"


def prepare_shared_paper_download(
    *,
    user,
    paper: PaperRecord,
    request_id: str = "",
) -> PreparedSharedPaperDownload:
    ensure_active_research_group_user(user)
    if paper.status != PaperRecord.Status.ACTIVE:
        message = "This paper is no longer available."
        record_paper_library_activity(
            actor=user,
            paper=paper,
            action=PaperLibraryActivity.Action.UNAVAILABLE_ACCESS,
            outcome=PaperLibraryActivity.Outcome.REJECTED,
            reason=message,
            request_id=request_id,
        )
        raise PaperDownloadUnavailable(message)

    storage_key, _storage_content_type = _active_paper_storage_metadata(paper)
    if not storage_key or not default_storage.exists(storage_key):
        message = "The paper file is no longer available."
        record_paper_library_activity(
            actor=user,
            paper=paper,
            action=PaperLibraryActivity.Action.DOWNLOAD_FAILED,
            outcome=PaperLibraryActivity.Outcome.FAILED,
            reason=message,
            request_id=request_id,
        )
        raise PaperDownloadUnavailable(message)

    metadata = paper_download_response_metadata(paper)
    record_paper_library_activity(
        actor=user,
        paper=paper,
        action=PaperLibraryActivity.Action.DOWNLOAD_STARTED,
        outcome=PaperLibraryActivity.Outcome.SUCCESS,
        request_id=request_id,
    )
    return PreparedSharedPaperDownload(
        storage_key=storage_key,
        filename=metadata["filename"],
        content_type=metadata["contentType"],
        content_disposition=metadata["contentDisposition"],
    )


def describe_shared_paper_download(
    *,
    user,
    paper: PaperRecord,
    request_id: str = "",
) -> dict:
    prepared = prepare_shared_paper_download(user=user, paper=paper, request_id=request_id)
    return {
        "filename": prepared.filename,
        "deliveryMode": "direct_response",
        "url": "",
        "expiresAt": timezone.now().isoformat().replace("+00:00", "Z"),
    }


def record_paper_library_activity(
    *,
    actor,
    action: str,
    outcome: str,
    paper: PaperRecord | None = None,
    paper_file=None,
    import_job: PaperImportJob | None = None,
    reason: str = "",
    request_id: str = "",
) -> PaperLibraryActivity:
    if reason and "/" in reason:
        reason = reason.rsplit("/", 1)[-1]
    return PaperLibraryActivity.objects.create(
        actor=actor if getattr(actor, "is_authenticated", False) else None,
        paper=paper,
        paper_file=paper_file,
        import_job=import_job,
        action=action,
        outcome=outcome,
        reason=reason[:255],
        request_id=request_id[:64],
    )
