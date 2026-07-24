import pytest

from apps.audit.models import AuditEvent
from tests.factories.accounts import UserFactory


@pytest.mark.django_db
def test_legacy_audit_rows_remain_readable_with_additive_defaults():
    actor = UserFactory()
    event = AuditEvent.objects.create(
        actor=actor,
        event_type="legacy.event",
        summary="Existing evidence",
    )

    event.refresh_from_db()
    assert event.summary == "Existing evidence"
    assert event.category == "other"
    assert event.outcome == "succeeded"
