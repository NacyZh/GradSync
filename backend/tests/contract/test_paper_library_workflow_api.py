import json
from io import BytesIO

import pytest
from django.core.files.uploadedfile import SimpleUploadedFile
from django.core.management import call_command
from django.urls import resolve
from pypdf import PdfWriter

from apps.library.import_services import import_shared_paper_pdf
from apps.library.models import DuplicateDetectionResult, PaperImportJob, PaperRecord
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


def _normalize_schema_path(path: str) -> str:
    path = path.removeprefix("/api")
    if path != "/" and path.endswith("/"):
        path = path[:-1]
    return (
        path.replace("{paper_id}", "{paperId}")
        .replace("{import_job_id}", "{importJobId}")
        .replace("{pk}", "{id}")
    )


def _schema_operations(schema):
    operations = {}
    for path, methods in schema.get("paths", {}).items():
        for method, operation in methods.items():
            if method.lower() in {"get", "post", "put", "patch", "delete"}:
                operations[(_normalize_schema_path(path), method.lower())] = operation
    return operations


def _query_parameters(operation):
    return {
        parameter.get("name")
        for parameter in operation.get("parameters", [])
        if parameter.get("in") == "query"
    }


def _request_content_types(operation):
    return set((operation.get("requestBody", {}).get("content") or {}).keys())


def test_generated_schema_covers_paper_library_workflow_contract(tmp_path):
    generated_path = tmp_path / "schema.json"
    call_command("spectacular", format="openapi-json", file=str(generated_path), verbosity=0)

    contract = {
        "paths": {
            "/library/papers/": {
                "get": {
                    "parameters": [
                        {"name": "q", "in": "query"},
                        {"name": "author", "in": "query"},
                        {"name": "year", "in": "query"},
                        {"name": "keyword", "in": "query"},
                    ],
                    "responses": {"200": {}, "401": {}, "403": {}},
                },
                "post": {
                    "requestBody": {"content": {"multipart/form-data": {}}},
                    "responses": {"202": {}, "400": {}, "401": {}, "403": {}, "413": {}},
                },
            },
            "/library/papers/{paperId}/": {
                "get": {"responses": {"200": {}, "401": {}, "403": {}, "404": {}}},
            },
            "/library/papers/{paperId}/download/": {
                "get": {"responses": {"200": {}, "401": {}, "403": {}, "404": {}}},
            },
            "/library/paper-imports/{importJobId}/": {
                "get": {"responses": {"200": {}, "401": {}, "403": {}, "404": {}}},
            },
            "/library/paper-imports/{importJobId}/review/": {
                "post": {
                    "requestBody": {"content": {"application/json": {}}},
                    "responses": {"200": {}, "400": {}, "401": {}, "403": {}, "404": {}},
                },
            },
        }
    }
    generated = json.loads(generated_path.read_text())
    contract_ops = _schema_operations(contract)
    generated_ops = _schema_operations(generated)

    missing_operations = sorted(set(contract_ops) - set(generated_ops))
    assert missing_operations == []

    for operation_key, contract_operation in contract_ops.items():
        generated_operation = generated_ops[operation_key]
        assert _query_parameters(contract_operation) <= _query_parameters(generated_operation)

        contract_request_types = _request_content_types(contract_operation)
        if contract_request_types:
            assert contract_request_types & _request_content_types(generated_operation)

        contract_statuses = set(contract_operation.get("responses", {}))
        generated_statuses = set(generated_operation.get("responses", {}))
        assert contract_statuses <= generated_statuses, operation_key


def _pdf(title: str = "Contract Paper", *, subject: str = "") -> bytes:
    output = BytesIO()
    writer = PdfWriter()
    writer.add_blank_page(width=612, height=792)
    metadata = {"/Title": title}
    if subject:
        metadata["/Subject"] = subject
    writer.add_metadata(metadata)
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


@pytest.mark.django_db
def test_ordinary_active_user_cannot_review_maintainer_import(api_client):
    owner = UserFactory(status="active")
    reviewer = UserFactory(status="active")
    import_shared_paper_pdf(
        user=owner,
        upload=SimpleUploadedFile(
            "base.pdf",
            _pdf("Graph Neural Methods for Research Groups"),
            content_type="application/pdf",
        ),
    )
    review_job = import_shared_paper_pdf(
        user=owner,
        upload=SimpleUploadedFile(
            "fuzzy.pdf",
            _pdf("Graph Neural Method for Research Group", subject="review"),
            content_type="application/pdf",
        ),
    )
    client = authenticate(api_client, reviewer)

    response = client.post(
        f"/api/library/paper-imports/{review_job.id}/review/",
        {"decision": "confirm_duplicate"},
        format="json",
    )

    assert response.status_code == 403


@pytest.mark.django_db
def test_maintainer_can_confirm_fuzzy_import_as_duplicate(api_client):
    owner = UserFactory(status="active")
    maintainer = UserFactory(status="active", global_role="advisor")
    accepted = import_shared_paper_pdf(
        user=owner,
        upload=SimpleUploadedFile(
            "base.pdf",
            _pdf("Graph Neural Methods for Research Groups"),
            content_type="application/pdf",
        ),
    )
    review_job = import_shared_paper_pdf(
        user=owner,
        upload=SimpleUploadedFile(
            "fuzzy.pdf",
            _pdf("Graph Neural Method for Research Group", subject="review"),
            content_type="application/pdf",
        ),
    )
    client = authenticate(api_client, maintainer)

    response = client.post(
        f"/api/library/paper-imports/{review_job.id}/review/",
        {"decision": "confirm_duplicate"},
        format="json",
    )

    assert response.status_code == 200
    assert response.data["status"] == PaperImportJob.Status.DUPLICATE
    assert response.data["duplicatePaper"]["id"] == accepted.accepted_paper_id
    assert response.data["duplicateDetection"]["reviewStatus"] == (
        DuplicateDetectionResult.ReviewStatus.CONFIRMED_DUPLICATE
    )


@pytest.mark.django_db
def test_maintainer_can_confirm_fuzzy_import_as_distinct(api_client):
    owner = UserFactory(status="active")
    maintainer = UserFactory(status="active", global_role="admin")
    import_shared_paper_pdf(
        user=owner,
        upload=SimpleUploadedFile(
            "base.pdf",
            _pdf("Graph Neural Methods for Research Groups"),
            content_type="application/pdf",
        ),
    )
    review_job = import_shared_paper_pdf(
        user=owner,
        upload=SimpleUploadedFile(
            "fuzzy.pdf",
            _pdf("Graph Neural Method for Research Group", subject="distinct"),
            content_type="application/pdf",
        ),
    )
    client = authenticate(api_client, maintainer)

    response = client.post(
        f"/api/library/paper-imports/{review_job.id}/review/",
        {"decision": "confirm_distinct"},
        format="json",
    )

    assert response.status_code == 200
    assert response.data["status"] == PaperImportJob.Status.ACCEPTED
    assert (
        response.data["acceptedPaper"]["canonicalTitle"]
        == "Graph Neural Method for Research Group"
    )
    assert response.data["duplicateDetection"]["reviewStatus"] == (
        DuplicateDetectionResult.ReviewStatus.CONFIRMED_DISTINCT
    )
    assert PaperRecord.objects.filter(status=PaperRecord.Status.ACTIVE).count() == 2
