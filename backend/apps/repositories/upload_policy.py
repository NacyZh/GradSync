from django.core.exceptions import ValidationError

CODE_MAX_BYTES = 200 * 1024 * 1024
ALLOWED_CODE_EXTENSIONS = {".zip", ".tar.gz"}
ALLOWED_CODE_CONTENT_TYPES = {
    "application/zip",
    "application/gzip",
    "application/x-gzip",
    "application/x-tar",
    "application/octet-stream",
}


def _extension(filename: str) -> str:
    filename = filename.lower()
    if filename.endswith(".tar.gz"):
        return ".tar.gz"
    return "." + filename.rsplit(".", 1)[-1] if "." in filename else ""


def validate_code_import(*, filename: str, content_type: str = "", size_bytes: int = 0) -> None:
    if size_bytes > CODE_MAX_BYTES:
        raise ValidationError("Code artifacts must be 200 MB or smaller")
    if _extension(filename) not in ALLOWED_CODE_EXTENSIONS:
        raise ValidationError("Code artifacts must be zip or tar.gz archives")
    if content_type and content_type not in ALLOWED_CODE_CONTENT_TYPES:
        raise ValidationError("Code artifact content type is not supported")
