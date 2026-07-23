from dataclasses import dataclass
from enum import StrEnum
from pathlib import PurePath

from django.conf import settings
from django.core.exceptions import ValidationError


class UploadCategory(StrEnum):
    PAPER = "paper"
    CODE = "code"
    DOCUMENT = "document"
    WRITING = "writing"
    FEEDBACK = "feedback"


@dataclass(frozen=True)
class UploadPolicyResult:
    category: str
    filename: str
    extension: str
    size_bytes: int
    content_type: str


def format_upload_size_label(size_bytes: int) -> str:
    size = int(size_bytes)
    units = [("GB", 1024**3), ("MB", 1024**2), ("KB", 1024)]
    for unit, factor in units:
        if size >= factor:
            value = size / factor
            formatted = f"{value:.1f}".rstrip("0").rstrip(".")
            return f"{formatted} {unit}"
    return f"{size} bytes"


def upload_policy_metadata(
    *,
    category: str,
    max_size_bytes: int,
    allowed_extensions: list[str],
    content_types: list[str],
) -> dict:
    limit = int(max_size_bytes)
    return {
        "category": category,
        "maxSizeBytes": limit,
        "displayLabel": format_upload_size_label(limit),
        "allowedExtensions": allowed_extensions,
        "contentTypes": content_types,
    }


def configured_upload_limit_bytes(category: UploadCategory | str) -> int:
    resolved = UploadCategory(str(category))
    return int(
        getattr(settings, "COLLABORATION_UPLOAD_LIMITS", {}).get(resolved.value, 0)
        or getattr(settings, "GRADSYNC_UPLOAD_MAX_BYTES", 0)
        or 0
    )


def configured_upload_policy(category: UploadCategory | str) -> dict:
    resolved = UploadCategory(str(category))
    return upload_policy_metadata(
        category=resolved.value,
        max_size_bytes=configured_upload_limit_bytes(resolved),
        allowed_extensions=sorted(ALLOWED_EXTENSIONS[resolved]),
        content_types=[],
    )


ALLOWED_EXTENSIONS = {
    UploadCategory.PAPER: {".pdf"},
    UploadCategory.CODE: {".zip", ".tar", ".gz", ".tgz", ".bz2", ".xz", ".7z"},
    UploadCategory.DOCUMENT: {
        ".pdf",
        ".doc",
        ".docx",
        ".xls",
        ".xlsx",
        ".ppt",
        ".pptx",
        ".txt",
        ".md",
    },
    UploadCategory.WRITING: {".doc", ".docx", ".tex", ".zip", ".tar", ".gz", ".tgz"},
    UploadCategory.FEEDBACK: {".pdf", ".doc", ".docx", ".txt", ".md"},
}


def validate_upload(upload, category: UploadCategory | str) -> UploadPolicyResult:
    resolved = UploadCategory(str(category))
    filename = PurePath(upload.name or "").name
    if not filename or filename != upload.name or ".." in PurePath(upload.name).parts:
        raise ValidationError("Unsafe filename is not allowed.")
    extension = PurePath(filename).suffix.lower()
    allowed = ALLOWED_EXTENSIONS[resolved]
    if extension not in allowed:
        if resolved == UploadCategory.CODE:
            raise ValidationError("Code uploads must be a compressed archive.")
        raise ValidationError(f"{resolved.value} uploads only allow: {', '.join(sorted(allowed))}.")
    size = int(getattr(upload, "size", 0) or 0)
    limit = configured_upload_limit_bytes(resolved)
    if limit and size > limit:
        label = format_upload_size_label(limit)
        raise ValidationError(f"Upload exceeds the {label} size limit.")
    return UploadPolicyResult(
        category=resolved.value,
        filename=filename,
        extension=extension,
        size_bytes=size,
        content_type=getattr(upload, "content_type", "") or "",
    )
