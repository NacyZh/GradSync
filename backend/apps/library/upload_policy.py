from django.conf import settings
from django.core.exceptions import ValidationError

from apps.common.upload_policy import upload_policy_metadata

PAPER_MAX_BYTES = 50 * 1024 * 1024
ALLOWED_PAPER_EXTENSIONS = {".pdf", ".bib", ".bibtex", ".txt"}
ALLOWED_PAPER_CONTENT_TYPES = {
    "application/pdf",
    "application/x-bibtex",
    "text/plain",
    "application/octet-stream",
}

SHARED_PAPER_ALLOWED_EXTENSIONS = [".pdf"]
SHARED_PAPER_CONTENT_TYPES = ["application/pdf"]


def shared_paper_upload_limit_bytes() -> int:
    return int(getattr(settings, "PAPER_LIBRARY_UPLOAD_LIMIT_BYTES", 0) or 0)


def shared_paper_upload_policy() -> dict:
    return upload_policy_metadata(
        category="paper",
        max_size_bytes=shared_paper_upload_limit_bytes(),
        allowed_extensions=SHARED_PAPER_ALLOWED_EXTENSIONS,
        content_types=SHARED_PAPER_CONTENT_TYPES,
    )


def shared_paper_oversized_message() -> str:
    return (
        "The selected PDF exceeds the "
        f"{shared_paper_upload_policy()['displayLabel']} upload size limit."
    )


def _extension(filename: str) -> str:
    filename = filename.lower()
    if filename.endswith(".tar.gz"):
        return ".tar.gz"
    return "." + filename.rsplit(".", 1)[-1] if "." in filename else ""


def validate_paper_import(*, filename: str, content_type: str = "", size_bytes: int = 0) -> None:
    if size_bytes > PAPER_MAX_BYTES:
        raise ValidationError("Paper attachments must be 50 MB or smaller")
    if _extension(filename) not in ALLOWED_PAPER_EXTENSIONS:
        raise ValidationError("Paper attachments must be PDF, BibTeX, or text metadata files")
    if content_type and content_type not in ALLOWED_PAPER_CONTENT_TYPES:
        raise ValidationError("Paper attachment content type is not supported")
