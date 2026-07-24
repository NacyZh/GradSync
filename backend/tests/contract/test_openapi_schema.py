from pathlib import Path

import pytest
import yaml


def test_feature_012_openapi_contract_has_canonical_and_compatibility_paths():
    contract = (
        Path(__file__).parents[3] / "specs/012-improve-resource-management/contracts/openapi.yaml"
    )
    if not contract.exists():
        pytest.skip("Feature 012 contract artifact is not included in this checkout")
    document = yaml.safe_load(contract.read_text(encoding="utf-8"))

    required_paths = {
        "/resources/",
        "/resources/availability/",
        "/resources/{resourceId}/",
        "/resources/{resourceId}/retire/",
        "/resource-types/",
        "/resource-types/{resourceTypeId}/",
        "/bookings/",
        "/bookings/{bookingId}/",
        "/bookings/{bookingId}/cancel/",
        "/bookings/{bookingId}/approve/",
        "/bookings/{bookingId}/reject/",
        "/resources/{resourceId}/use-submissions/",
        "/resource-use-submissions/",
        "/resource-use-submissions/{submissionId}/",
        "/projects/{projectId}/bookings/",
    }
    assert set(document["paths"]) == required_paths


def test_feature_016_openapi_contract_covers_access_governance_operations():
    contract = (
        Path(__file__).parents[3]
        / "specs/016-access-governance/contracts/openapi.yaml"
    )
    document = yaml.safe_load(contract.read_text(encoding="utf-8"))
    operations = {
        (path, method)
        for path, path_item in document["paths"].items()
        for method in path_item
        if method in {"get", "post", "patch", "put", "delete"}
    }
    required = {
        ("/accounts/password-recovery/", "post"),
        ("/accounts/password-recovery/confirm/", "post"),
        ("/accounts/me/email-change/", "get"),
        ("/accounts/me/email-change/", "post"),
        ("/accounts/me/email-change/", "delete"),
        ("/accounts/me/sessions/", "get"),
        ("/accounts/me/sessions/{session_id}/", "delete"),
        ("/accounts/teachers/", "get"),
        ("/projects/{project_id}/members/", "post"),
        ("/projects/{project_id}/members/{membership_id}/", "patch"),
        ("/projects/{project_id}/ownership-transfer/", "post"),
        ("/projects/{project_id}/review-assignments/", "post"),
        ("/audit-events", "get"),
        ("/audit-events/{event_id}", "get"),
        ("/audit-exports", "post"),
        ("/audit-exports/{export_id}/download", "get"),
    }
    assert required <= operations
