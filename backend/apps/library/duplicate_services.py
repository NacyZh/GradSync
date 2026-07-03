import re
from dataclasses import dataclass

from .models import PaperAttachment, PaperRecord


@dataclass(frozen=True)
class DuplicateMatch:
    paper: PaperRecord
    reason: str


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
