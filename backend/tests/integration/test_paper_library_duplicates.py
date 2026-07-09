from io import BytesIO

import pytest
from django.core.files.uploadedfile import SimpleUploadedFile
from pypdf import PdfWriter

from apps.library.models import DuplicateDetectionResult, PaperImportJob, PaperRecord
from apps.library.services.imports import import_shared_paper_pdf
from tests.factories.accounts import UserFactory


def _pdf(title: str, *, author: str = "", subject: str = "") -> bytes:
    output = BytesIO()
    writer = PdfWriter()
    writer.add_blank_page(width=612, height=792)
    metadata = {"/Title": title}
    if author:
        metadata["/Author"] = author
    if subject:
        metadata["/Subject"] = subject
    writer.add_metadata(metadata)
    writer.write(output)
    return output.getvalue()


def _upload(content: bytes, name: str = "paper.pdf") -> SimpleUploadedFile:
    return SimpleUploadedFile(name, content, content_type="application/pdf")


@pytest.mark.django_db
def test_reuploading_same_pdf_is_duplicate_without_second_active_paper():
    user = UserFactory(status="active")
    content = _pdf("Duplicate Fingerprint Paper")
    accepted = import_shared_paper_pdf(user=user, upload=_upload(content, "first.pdf"))

    duplicate = import_shared_paper_pdf(user=user, upload=_upload(content, "renamed.pdf"))

    assert accepted.status == PaperImportJob.Status.ACCEPTED
    assert duplicate.status == PaperImportJob.Status.DUPLICATE
    assert duplicate.duplicate_paper_id == accepted.accepted_paper_id
    assert PaperRecord.objects.filter(status=PaperRecord.Status.ACTIVE).count() == 1
    result = duplicate.paper_file.duplicate_detection_results.first()
    assert result.decision == DuplicateDetectionResult.Decision.DUPLICATE_FILE_FINGERPRINT


@pytest.mark.django_db
def test_strong_metadata_duplicate_does_not_create_active_paper():
    user = UserFactory(status="active")
    accepted = import_shared_paper_pdf(
        user=user,
        upload=_upload(_pdf("Strong Metadata Paper", author="Ada Lovelace"), "first.pdf"),
    )

    duplicate = import_shared_paper_pdf(
        user=user,
        upload=_upload(
            _pdf("Strong Metadata Paper", author="Ada Lovelace", subject="distinct bytes"),
            "second.pdf",
        ),
    )

    assert duplicate.status == PaperImportJob.Status.DUPLICATE
    assert duplicate.duplicate_paper_id == accepted.accepted_paper_id
    assert PaperRecord.objects.filter(canonical_title="Strong Metadata Paper").count() == 1
    result = duplicate.paper_file.duplicate_detection_results.first()
    assert result.decision == DuplicateDetectionResult.Decision.DUPLICATE_METADATA_STRONG_MATCH


@pytest.mark.django_db
def test_fuzzy_duplicate_enters_maintainer_review_without_active_paper():
    user = UserFactory(status="active")
    import_shared_paper_pdf(
        user=user,
        upload=_upload(_pdf("Graph Neural Methods for Research Groups"), "first.pdf"),
    )

    review = import_shared_paper_pdf(
        user=user,
        upload=_upload(_pdf("Graph Neural Method for Research Group"), "fuzzy.pdf"),
    )

    assert review.status == PaperImportJob.Status.MAINTAINER_REVIEW
    assert review.accepted_paper_id is None
    assert PaperRecord.objects.filter(status=PaperRecord.Status.ACTIVE).count() == 1
    result = review.paper_file.duplicate_detection_results.first()
    assert result.decision == DuplicateDetectionResult.Decision.MAINTAINER_REVIEW
    assert result.review_status == DuplicateDetectionResult.ReviewStatus.PENDING
