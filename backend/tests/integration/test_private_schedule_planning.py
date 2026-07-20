from datetime import timedelta

import pytest
from django.utils import timezone

from apps.schedules.models import ScheduleItem, ScheduleOccurrenceException
from apps.schedules.services import complete_schedule, update_schedule
from tests.factories.accounts import UserFactory

pytestmark = pytest.mark.django_db


def recurring_item(owner):
    starts_at = timezone.now() + timedelta(days=1)
    return ScheduleItem.objects.create(
        owner=owner,
        organizer=owner,
        title="Monthly private plan",
        starts_at=starts_at,
        ends_at=starts_at + timedelta(hours=1),
        timezone="UTC",
        recurrence_frequency="daily",
        recurrence_interval=1,
        recurrence_until=(starts_at + timedelta(days=10)).date(),
    )


def test_occurrence_update_and_completion_leave_series_fields_unchanged():
    owner = UserFactory()
    item = recurring_item(owner)
    occurrence_key = (item.starts_at + timedelta(days=2)).isoformat()

    update_schedule(
        item=item,
        actor=owner,
        expected_version=1,
        change_scope="occurrence",
        occurrence_key=occurrence_key,
        fields={"title": "One changed occurrence"},
    )
    item.refresh_from_db()
    assert item.title == "Monthly private plan"
    exception = ScheduleOccurrenceException.objects.get(schedule_item=item)
    assert exception.override_title == "One changed occurrence"

    complete_schedule(
        item=item,
        actor=owner,
        expected_version=2,
        change_scope="occurrence",
        occurrence_key=occurrence_key,
    )
    exception.refresh_from_db()
    assert exception.status == ScheduleOccurrenceException.Status.COMPLETED
    assert item.status == ScheduleItem.Status.ACTIVE
