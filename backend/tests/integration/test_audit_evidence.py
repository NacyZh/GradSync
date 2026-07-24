import pytest

from apps.audit.models import AuditEvent
from apps.audit.services import record_event
from tests.factories.accounts import UserFactory


@pytest.mark.django_db
def test_audit_event_records_safe_actor_and_correlation_context():
    actor = UserFactory(global_role="advisor")

    event = record_event(
        None,
        actor,
        "account_security.session_revoked",
        "Session revoked",
        category="account_security",
        outcome="succeeded",
        correlation_id="a" * 32,
        target_snapshot={"status": "revoked", "token": "secret"},
        allowed_snapshot_keys={"status"},
    )

    assert event.actor_snapshot["id"] == actor.id
    assert event.actor_snapshot["role"] == "advisor"
    assert event.correlation_id == "a" * 32
    assert event.target_snapshot == {"status": "revoked"}
    assert AuditEvent.objects.filter(pk=event.pk).exists()
