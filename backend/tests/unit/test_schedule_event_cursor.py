from datetime import timedelta

import pytest
from django.utils import timezone

from apps.schedules.event_services import decode_event_cursor, schedule_events_visible_to
from apps.schedules.models import ScheduleItem, ScheduleRecipientGrant
from tests.factories.accounts import UserFactory

pytestmark = pytest.mark.django_db


def test_event_cursor_is_opaque_and_private_events_are_owner_only():
    owner = UserFactory()
    other = UserFactory()
    item = ScheduleItem.objects.create(
        owner=owner,
        organizer=owner,
        title="Never in cursor",
        description="Private details",
        starts_at=timezone.now(),
        ends_at=timezone.now() + timedelta(hours=1),
    )

    events = schedule_events_visible_to(owner)
    assert len(events) == 1
    assert "Never in cursor" not in str(events)
    assert decode_event_cursor(events[0]["cursor"])[1] == item.id
    assert schedule_events_visible_to(other) == []


def test_group_event_cursor_is_visible_to_current_recipient_without_content():
    owner = UserFactory(global_role="advisor")
    recipient = UserFactory()
    item = ScheduleItem.objects.create(
        owner=owner,
        organizer=owner,
        scope="group",
        title="Sensitive group title",
        starts_at=timezone.now(),
        ends_at=timezone.now() + timedelta(hours=1),
        published_at=timezone.now(),
    )
    ScheduleRecipientGrant.objects.create(
        schedule_item=item,
        recipient=recipient,
        valid_from=timezone.now() - timedelta(minutes=1),
        source_types=["account"],
    )

    events = schedule_events_visible_to(recipient)
    assert len(events) == 1
    assert "Sensitive group title" not in str(events)
