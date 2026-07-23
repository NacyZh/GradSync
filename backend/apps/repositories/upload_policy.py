from django.conf import settings
from django.core.exceptions import ValidationError

from apps.common.upload_policy import (
    ALLOWED_EXTENSIONS,
    UploadCategory,
    configured_upload_limit_bytes,
    format_upload_size_label,
    upload_policy_metadata,
)

ALLOWED_CODE_EXTENSIONS = {".zip", ".tar.gz"}
ALLOWED_CODE_CONTENT_TYPES = {
    "application/zip",
    "application/gzip",
    "application/x-gzip",
    "application/x-tar",
    "application/octet-stream",
}
CODE_ARCHIVE_UPLOAD_CONTENT_TYPES = [
    "application/zip",
    "application/gzip",
    "application/x-gzip",
    "application/x-tar",
    "application/octet-stream",
]


def code_archive_upload_policy() -> dict:
    return upload_policy_metadata(
        category=UploadCategory.CODE.value,
        max_size_bytes=int(
            getattr(settings, "COLLABORATION_UPLOAD_LIMITS", {}).get(
                UploadCategory.CODE.value, 0
            )
            or 0
        ),
        allowed_extensions=sorted(ALLOWED_EXTENSIONS[UploadCategory.CODE]),
        content_types=CODE_ARCHIVE_UPLOAD_CONTENT_TYPES,
    )


def _extension(filename: str) -> str:
    filename = filename.lower()
    if filename.endswith(".tar.gz"):
        return ".tar.gz"
    return "." + filename.rsplit(".", 1)[-1] if "." in filename else ""


def validate_code_import(*, filename: str, content_type: str = "", size_bytes: int = 0) -> None:
    limit = configured_upload_limit_bytes(UploadCategory.CODE)
    if limit and size_bytes > limit:
        raise ValidationError(
            f"Code artifact exceeds the {format_upload_size_label(limit)} size limit"
        )
    if _extension(filename) not in ALLOWED_CODE_EXTENSIONS:
        raise ValidationError("Code artifacts must be zip or tar.gz archives")
    if content_type and content_type not in ALLOWED_CODE_CONTENT_TYPES:
        raise ValidationError("Code artifact content type is not supported")
