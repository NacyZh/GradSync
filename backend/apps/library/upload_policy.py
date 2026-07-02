from django.core.exceptions import ValidationError

PAPER_MAX_BYTES = 50 * 1024 * 1024
ALLOWED_PAPER_EXTENSIONS = {".pdf", ".bib", ".bibtex", ".txt"}
ALLOWED_PAPER_CONTENT_TYPES = {
    "application/pdf",
    "application/x-bibtex",
    "text/plain",
    "application/octet-stream",
}


def _extension(filename: str) -> str:
    filename = filename.lower()
    if filename.endswith(".tar.gz"):
        return ".tar.gz"
    return "." + filename.rsplit(".", 1)[-1] if "." in filename else ""


def validate_paper_upload(*, filename: str, content_type: str = "", size_bytes: int = 0) -> None:
    if size_bytes > PAPER_MAX_BYTES:
        raise ValidationError("Paper attachments must be 50 MB or smaller")
    if _extension(filename) not in ALLOWED_PAPER_EXTENSIONS:
        raise ValidationError("Paper attachments must be PDF, BibTeX, or text metadata files")
    if content_type and content_type not in ALLOWED_PAPER_CONTENT_TYPES:
        raise ValidationError("Paper attachment content type is not supported")
