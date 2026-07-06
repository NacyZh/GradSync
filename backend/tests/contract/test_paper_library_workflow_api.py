from io import BytesIO

import pytest
from django.core.files.uploadedfile import SimpleUploadedFile
from django.urls import resolve
from pypdf import PdfWriter

from apps.library.models import PaperImportJob
from apps.library.serializers import (
    DuplicateDetectionResultSerializer,
    PaperImportJobSerializer,
    PaperRecordSerializer,
    PaperTitleExtractionResultSerializer,
    UploadErrorSerializer,
)
from tests.factories.accounts import UserFactory
from tests.helpers import authenticate


@pytest.mark.parametrize(
    ("path", "view_name"),
    [
        ("/api/library/papers/", "shared-paper-list"),
        ("/api/library/papers/1/", "shared-paper-detail"),
        ("/api/library/papers/1/download/", "shared-paper-download"),
        ("/api/library/paper-imports/1/", "paper-import-status"),
        ("/api/library/paper-imports/1/review/", "paper-import-review"),
    ],
)
def test_paper_library_workflow_routes_resolve(path, view_name):
    assert resolve(path).url_name == view_name


def test_paper_library_workflow_serializers_expose_openapi_fields():
    paper_fields = set(PaperRecordSerializer().fields)
    import_fields = set(PaperImportJobSerializer().fields)
    extraction_fields = set(PaperTitleExtractionResultSerializer().fields)
    duplicate_fields = set(DuplicateDetectionResultSerializer().fields)
    error_fields = set(UploadErrorSerializer().fields)

    assert {
        "canonicalTitle",
        "titleSource",
        "downloadAvailable",
        "defaultDownloadFilename",
    } <= paper_fields
    assert {
        "status",
        "acceptedPaper",
        "duplicatePaper",
        "extraction",
        "duplicateDetection",
    } <= import_fields
    assert {"source", "extractedTitle", "confidence", "failureReason"} <= extraction_fields
    assert {"decision", "matchBasis", "candidatePaperId", "reviewStatus"} <= duplicate_fields
    assert {"code", "message", "reason"} <= error_fields


def _pdf(title: str = "Contract Paper") -> bytes:
    output = BytesIO()
    writer = PdfWriter()
    writer.add_blank_page(width=612, height=792)
    writer.add_metadata({"/Title": title})
    writer.write(output)
    return output.getvalue()


@pytest.mark.django_db
def test_shared_paper_import_accepts_file_only(api_client):
    user = UserFactory(status="active")
    client = authenticate(api_client, user)

    response = client.post(
        "/api/library/papers/",
        {
            "file": SimpleUploadedFile(
                "local-name.pdf",
                _pdf("Contract Extracted Title"),
                content_type="application/pdf",
            )
        },
        format="multipart",
    )

    assert response.status_code == 202
    assert response.data["status"] == PaperImportJob.Status.ACCEPTED
    assert response.data["acceptedPaper"]["canonicalTitle"] == "Contract Extracted Title"
    assert response.data["extraction"]["source"] == "embedded_metadata"

    status_response = client.get(f"/api/library/paper-imports/{response.data['id']}/")

    assert status_response.status_code == 200
    assert status_response.data["status"] == PaperImportJob.Status.ACCEPTED


@pytest.mark.django_db
def test_shared_paper_import_rejects_extra_metadata_fields(api_client):
    user = UserFactory(status="active")
    client = authenticate(api_client, user)

    response = client.post(
        "/api/library/papers/",
        {
            "file": SimpleUploadedFile(
                "local-name.pdf",
                _pdf("Contract Extracted Title"),
                content_type="application/pdf",
            ),
            "title": "User typed title",
        },
        format="multipart",
    )

    assert response.status_code == 400
    assert response.data["reason"] == "metadata_fields_not_allowed"
