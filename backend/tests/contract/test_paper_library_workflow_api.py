import pytest
from django.urls import resolve

from apps.library.serializers import (
    DuplicateDetectionResultSerializer,
    PaperImportJobSerializer,
    PaperRecordSerializer,
    PaperTitleExtractionResultSerializer,
    UploadErrorSerializer,
)


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
