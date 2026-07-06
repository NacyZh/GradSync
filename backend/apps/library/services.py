from __future__ import annotations

from django.core.exceptions import PermissionDenied
from django.db.models import Q, QuerySet

from apps.accounts.models import User

from .models import PaperImportJob, PaperLibraryActivity, PaperRecord


def is_active_research_group_user(user) -> bool:
    return bool(
        getattr(user, "is_authenticated", False)
        and getattr(user, "status", None) == User.Status.ACTIVE
    )


def ensure_active_research_group_user(user) -> None:
    if not is_active_research_group_user(user):
        raise PermissionDenied("Active account required for the shared paper library.")


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
        queryset = queryset.filter(publication_year=year)
    keyword = params.get("keyword") or params.get("tag")
    if keyword:
        queryset = queryset.filter(tags__icontains=keyword)
    return queryset


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
