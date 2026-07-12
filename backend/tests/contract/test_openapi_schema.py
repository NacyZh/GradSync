from pathlib import Path

import yaml


def test_feature_012_openapi_contract_has_canonical_and_compatibility_paths():
    contract = (
        Path(__file__).parents[3]
        / "specs/012-improve-resource-management/contracts/openapi.yaml"
    )
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
