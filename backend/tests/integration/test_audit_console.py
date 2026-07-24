import pytest

from apps.audit.models import AuditEvent
from tests.factories.accounts import VerifiedUserFactory


@pytest.mark.django_db
def test_cursor_order_is_stable_and_search_is_audited(api_client):
    admin = VerifiedUserFactory(global_role="admin", active_role="administrator")
    AuditEvent.objects.bulk_create(
        [
            AuditEvent(
                actor=admin,
                category="material",
                event_type=f"material.event.{index}",
                summary=f"Material event {index}",
            )
            for index in range(3)
        ]
    )
    api_client.force_authenticate(admin)

    first = api_client.get("/api/audit-events", {"category": "material", "limit": 2})
    assert first.status_code == 200
    assert len(first.json()["results"]) == 2
    second = api_client.get(
        "/api/audit-events",
        {"category": "material", "limit": 2, "cursor": first.json()["nextCursor"]},
    )
    assert second.status_code == 200
    first_ids = {row["id"] for row in first.json()["results"]}
    second_ids = {row["id"] for row in second.json()["results"]}
    assert first_ids.isdisjoint(second_ids)
    assert AuditEvent.objects.filter(event_type="audit_access.search").exists()

