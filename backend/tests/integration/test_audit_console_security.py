import pytest

from apps.audit.models import AuditEvent
from tests.factories.accounts import VerifiedUserFactory


@pytest.mark.django_db
def test_non_administrator_receives_no_audit_metadata(api_client):
    user = VerifiedUserFactory(global_role="advisor", active_role="teacher")
    event = AuditEvent.objects.create(
        actor=user,
        event_type="secret.test",
        summary="Hidden event",
        target_snapshot={"token": "must-not-appear"},
    )
    api_client.force_authenticate(user)

    for path in (
        "/api/audit-events",
        f"/api/audit-events/{event.id}",
        "/api/audit-exports",
    ):
        response = api_client.get(path)
        assert response.status_code == 403
        assert "Hidden event" not in str(response.data)
        assert "must-not-appear" not in str(response.data)

