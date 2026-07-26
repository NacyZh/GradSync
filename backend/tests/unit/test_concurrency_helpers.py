import pytest
from django.utils import timezone

from apps.common.concurrency import (
    VersionConflict,
    idempotent_mutation,
    require_expected_version,
)
from apps.notifications.models import Notification
from tests.factories.accounts import VerifiedUserFactory


class Record:
    pk = 7
    version = 3
    secret = "hidden"


def test_expected_version_returns_safe_current_state():
    with pytest.raises(VersionConflict) as conflict:
        require_expected_version(Record(), 2)

    assert conflict.value.current_state == {"id": 7, "version": 3}


def test_matching_expected_version_returns_record():
    record = Record()
    assert require_expected_version(record, 3) is record


@pytest.mark.django_db
def test_duplicate_idempotency_key_returns_one_effective_mutation():
    recipient = VerifiedUserFactory()
    lookup = {
        "recipient": recipient,
        "dedupe_key": "notification:dedupe",
        "active_follow_up": True,
    }

    def create():
        return Notification.objects.create(
            **lookup,
            event_type=Notification.EventType.PENDING_REVIEW,
            target_type="WeeklyProgressReport",
            target_id="1",
            subject="Review",
            eligible_at=timezone.now(),
            requirement_type=Notification.RequirementType.ACTION,
            outcome_state=Notification.OutcomeState.PENDING,
        )

    first, first_created = idempotent_mutation(Notification, lookup=lookup, mutation=create)
    second, second_created = idempotent_mutation(Notification, lookup=lookup, mutation=create)

    assert first.pk == second.pk
    assert first_created is True
    assert second_created is False
