import pytest

from apps.audit.models import AuditEvent
from tests.factories.accounts import VerifiedUserFactory


@pytest.mark.django_db
def test_administrator_filters_inspects_and_requests_audit_export(api_client):
    admin = VerifiedUserFactory(global_role="admin", active_role="administrator")
    event = AuditEvent.objects.create(
        actor=admin,
        category=AuditEvent.Category.PROJECT_GOVERNANCE,
        event_type="project_governance.changed",
        target_type="ResearchProject",
        target_id="7",
        summary="Governance changed",
    )
    api_client.force_authenticate(admin)

    listing = api_client.get(
        "/api/audit-events",
        {"category": "project_governance", "limit": 20},
    )
    assert listing.status_code == 200
    assert listing.json()["results"][0]["id"] == event.id
    detail = api_client.get(f"/api/audit-events/{event.id}")
    assert detail.status_code == 200
    assert detail.json()["capabilities"]["canExport"] is True
    export = api_client.post(
        "/api/audit-exports",
        {"filters": {"category": "project_governance"}},
        format="json",
    )
    assert export.status_code == 202
    assert export.json()["status"] in {"queued", "ready"}


@pytest.mark.django_db
def test_audit_export_rejects_empty_scope(api_client):
    admin = VerifiedUserFactory(global_role="admin", active_role="administrator")
    api_client.force_authenticate(admin)
    response = api_client.post("/api/audit-exports", {"filters": {}}, format="json")
    assert response.status_code == 400

