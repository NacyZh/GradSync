from io import BytesIO

import pytest
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import override_settings
from pypdf import PdfWriter

from apps.library import services as library_services
from apps.library.models import PaperImportJob, PaperRecord
from apps.library.services import paper_upload_policy
from apps.library.services.imports import (
    PaperImportError,
    import_shared_paper_pdf,
    validate_pdf_upload,
)
from tests.factories.accounts import UserFactory


def _pdf(title: str = "Validation Paper") -> bytes:
    output = BytesIO()
    writer = PdfWriter()
    writer.add_blank_page(width=612, height=792)
    writer.add_metadata({"/Title": title})
    writer.write(output)
    return output.getvalue()


def _encrypted_pdf() -> bytes:
    output = BytesIO()
    writer = PdfWriter()
    writer.add_blank_page(width=612, height=792)
    writer.encrypt("secret")
    writer.write(output)
    return output.getvalue()


def _upload(
    content: bytes,
    *,
    name: str = "paper.pdf",
    content_type: str = "application/pdf",
) -> SimpleUploadedFile:
    return SimpleUploadedFile(name, content, content_type=content_type)


def test_pdf_validation_returns_fingerprint_for_valid_pdf():
    validated = validate_pdf_upload(_upload(_pdf()))

    assert validated.file_fingerprint
    assert validated.size_bytes > 0


@pytest.mark.parametrize(
    ("upload", "reason"),
    [
        (_upload(b"text", name="paper.txt", content_type="text/plain"), "unsupported_type"),
        (_upload(b"", name="empty.pdf"), "empty_file"),
        (_upload(b"%PDF bad", name="bad.pdf"), "corrupted_pdf"),
        (_upload(_encrypted_pdf(), name="locked.pdf"), "password_blocked"),
    ],
)
def test_pdf_validation_rejects_invalid_uploads(upload, reason):
    with pytest.raises(PaperImportError) as exc_info:
        validate_pdf_upload(upload)

    assert exc_info.value.reason == reason


def test_pdf_validation_rejects_unsafe_path():
    upload = _upload(_pdf())
    upload._name = "../private.pdf"

    with pytest.raises(PaperImportError) as exc_info:
        validate_pdf_upload(upload)

    assert exc_info.value.reason == "unsafe_path"


@override_settings(PAPER_LIBRARY_UPLOAD_LIMIT_BYTES=12)
def test_pdf_validation_rejects_oversized_upload():
    with pytest.raises(PaperImportError) as exc_info:
        validate_pdf_upload(_upload(_pdf()))

    assert exc_info.value.reason == "oversized"


def test_pdf_validation_allows_exact_upload_size_boundary():
    content = _pdf("Exact Boundary Paper")

    with override_settings(PAPER_LIBRARY_UPLOAD_LIMIT_BYTES=len(content)):
        validated = validate_pdf_upload(_upload(content))

    assert validated.size_bytes == len(content)


def test_pdf_validation_allows_three_megabyte_pdf_under_production_limit():
    content = _pdf("Three Megabyte Paper")
    content += b"\0" * ((3 * 1024 * 1024) - len(content))

    with override_settings(PAPER_LIBRARY_UPLOAD_LIMIT_BYTES=100 * 1024 * 1024):
        validated = validate_pdf_upload(_upload(content))

    assert validated.size_bytes == 3 * 1024 * 1024


def test_pdf_validation_oversized_message_repeats_policy_display_label():
    content = _pdf("Oversized Boundary Paper")
    limit = len(content) - 1

    with override_settings(PAPER_LIBRARY_UPLOAD_LIMIT_BYTES=limit):
        policy = paper_upload_policy()
        with pytest.raises(PaperImportError) as exc_info:
            validate_pdf_upload(_upload(content))

    assert exc_info.value.reason == "oversized"
    assert policy["displayLabel"] in exc_info.value.message


@pytest.mark.django_db
def test_shared_import_rejects_missing_title_with_specific_job_reason():
    user = UserFactory(status="active")

    job = import_shared_paper_pdf(user=user, upload=_upload(_pdf("")))

    assert job.status == PaperImportJob.Status.REJECTED
    assert job.failure_reason == PaperImportJob.FailureReason.MISSING_RELIABLE_TITLE
    assert PaperRecord.objects.count() == 0


@override_settings(PAPER_LIBRARY_UPLOAD_LIMIT_BYTES=2 * 1024 * 1024)
def test_paper_upload_policy_formats_effective_size_for_display():
    policy = paper_upload_policy()

    assert policy == {
        "category": "paper",
        "maxSizeBytes": 2 * 1024 * 1024,
        "displayLabel": "2 MB",
        "allowedExtensions": [".pdf"],
        "contentTypes": ["application/pdf"],
    }


@override_settings(PAPER_LIBRARY_UPLOAD_LIMIT_BYTES=1536)
def test_paper_upload_policy_formats_small_limits_without_ui_drift():
    policy = paper_upload_policy()

    assert policy["maxSizeBytes"] == 1536
    assert policy["displayLabel"] == "1.5 KB"


def test_import_services_remain_available_through_library_service_exports():
    assert library_services.PaperImportError is PaperImportError
    assert library_services.import_shared_paper_pdf is import_shared_paper_pdf
    assert library_services.validate_pdf_upload is validate_pdf_upload
