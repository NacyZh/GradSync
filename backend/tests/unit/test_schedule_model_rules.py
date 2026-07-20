from datetime import date, timedelta

import pytest
from django.core.exceptions import ValidationError
from django.db import IntegrityError, transaction
from django.utils import timezone

from apps.audit.services import record_schedule_event
from apps.schedules.models import (
    ScheduleAudience,
    ScheduleItem,
    ScheduleNotificationDispatch,
    ScheduleOccurrenceException,
    ScheduleRecipientGrant,
    ScheduleReminder,
    ScheduleRevision,
)
from tests.factories.accounts import UserFactory
from tests.factories.collaboration import ResearchProjectFactory

pytestmark = pytest.mark.django_db


def test_timed_and_all_day_shapes_are_exclusive():
    owner = UserFactory()
    item = ScheduleItem(
        owner=owner,
        organizer=owner,
        title="Mixed range",
        all_day=True,
        starts_at=timezone.now(),
        ends_at=timezone.now() + timedelta(hours=1),
        starts_on=date.today(),
        ends_on=date.today() + timedelta(days=1),
    )

    with pytest.raises(ValidationError):
        item.full_clean()


def test_recurring_item_requires_bounded_until():
    owner = UserFactory()
    item = ScheduleItem(
        owner=owner,
        organizer=owner,
        title="Unbounded",
        starts_at=timezone.now(),
        ends_at=timezone.now() + timedelta(hours=1),
        recurrence_frequency=ScheduleItem.RecurrenceFrequency.DAILY,
    )

    with pytest.raises(ValidationError):
        item.full_clean()


def test_audience_shape_and_open_grant_are_unique():
    owner = UserFactory(global_role="advisor")
    recipient = UserFactory()
    project = ResearchProjectFactory(advisor=owner)
    item = ScheduleItem.objects.create(
        owner=owner,
        organizer=owner,
        scope=ScheduleItem.Scope.GROUP,
        title="Lab meeting",
        starts_at=timezone.now(),
        ends_at=timezone.now() + timedelta(hours=1),
        published_at=timezone.now(),
    )
    audience = ScheduleAudience(
        schedule_item=item,
        scope_type=ScheduleAudience.ScopeType.PROJECT,
        project=project,
        account=recipient,
        created_by=owner,
    )
    with pytest.raises(ValidationError):
        audience.full_clean()

    ScheduleRecipientGrant.objects.create(
        schedule_item=item,
        recipient=recipient,
        valid_from=timezone.now(),
        source_types=["project"],
        source_project_ids=[project.id],
    )
    with pytest.raises(IntegrityError):
        ScheduleRecipientGrant.objects.create(
            schedule_item=item,
            recipient=recipient,
            valid_from=timezone.now(),
            source_types=["account"],
        )


def test_exception_reminder_revision_and_dispatch_constraints():
    owner = UserFactory(global_role="advisor")
    item = ScheduleItem.objects.create(
        owner=owner,
        organizer=owner,
        scope=ScheduleItem.Scope.GROUP,
        title="Review",
        starts_at=timezone.now(),
        ends_at=timezone.now() + timedelta(hours=1),
        published_at=timezone.now(),
    )
    exception = ScheduleOccurrenceException(schedule_item=item, created_by=owner)
    with pytest.raises(ValidationError):
        exception.full_clean()

    reminder = ScheduleReminder(schedule_item=item, offset_minutes=12)
    with pytest.raises(ValidationError):
        reminder.full_clean()

    ScheduleRevision.objects.create(
        schedule_item=item,
        revision_number=1,
        actor=owner,
        change_type=ScheduleRevision.ChangeType.PUBLISHED,
    )
    with pytest.raises(IntegrityError), transaction.atomic():
        ScheduleRevision.objects.create(
            schedule_item=item,
            revision_number=1,
            actor=owner,
            change_type=ScheduleRevision.ChangeType.CHANGED,
        )

    dispatch = ScheduleNotificationDispatch(
        schedule_item=item,
        recipient=owner,
        occurrence_key="2026-07-20T08:00:00Z",
        event_type=ScheduleNotificationDispatch.EventType.REMINDER,
        channel=ScheduleNotificationDispatch.Channel.IN_APP,
    )
    with pytest.raises(ValidationError):
        dispatch.full_clean()


def test_group_schedule_audit_omits_private_content():
    owner = UserFactory(global_role="advisor")
    item = ScheduleItem.objects.create(
        owner=owner,
        organizer=owner,
        scope="group",
        title="Sensitive title",
        description="Sensitive description",
        starts_at=timezone.now(),
        ends_at=timezone.now() + timedelta(hours=1),
        published_at=timezone.now(),
    )

    event = record_schedule_event(
        actor=owner,
        schedule_item=item,
        action="published",
        outcome="created",
        audience={"projects": 1, "recipients": 4},
    )

    payload = str(event.target_snapshot)
    assert "Sensitive title" not in payload
    assert "Sensitive description" not in payload
    assert event.target_snapshot["audience"]["recipients"] == 4
