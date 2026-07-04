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
    limit = int(getattr(settings, "COLLABORATION_UPLOAD_LIMITS", {}).get(resolved.value, 0) or 0)
    if limit and size > limit:
        raise ValidationError(f"Upload exceeds the {resolved.value} size limit.")
    return UploadPolicyResult(
        category=resolved.value,
        filename=filename,
        extension=extension,
        size_bytes=size,
        content_type=getattr(upload, "content_type", "") or "",
    )
