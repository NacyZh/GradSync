import pytest
from django.core.exceptions import ValidationError
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import override_settings

from apps.common.upload_policy import UploadCategory, validate_upload


def test_paper_upload_accepts_pdf_under_configured_limit():
    upload = SimpleUploadedFile("paper.pdf", b"%PDF-1.7", content_type="application/pdf")

    result = validate_upload(upload, UploadCategory.PAPER)

    assert result.category == "paper"
    assert result.extension == ".pdf"


@override_settings(COLLABORATION_UPLOAD_LIMITS={"paper": 4})
def test_upload_policy_uses_configurable_size_limit():
    upload = SimpleUploadedFile("paper.pdf", b"12345", content_type="application/pdf")

    with pytest.raises(ValidationError, match="exceeds"):
        validate_upload(upload, UploadCategory.PAPER)


def test_code_upload_rejects_non_archive_files():
    upload = SimpleUploadedFile("analysis.py", b"print(1)", content_type="text/x-python")

    with pytest.raises(ValidationError, match="compressed archive"):
        validate_upload(upload, UploadCategory.CODE)


def test_upload_policy_rejects_unsafe_paths():
    class UnsafeUpload:
        name = "../paper.pdf"
        size = 4
        content_type = "application/pdf"

    with pytest.raises(ValidationError, match="Unsafe filename"):
        validate_upload(UnsafeUpload(), UploadCategory.PAPER)
