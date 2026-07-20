import pytest
from django.utils import timezone

from apps.schedules.models import ScheduleItem, ScheduleRevision
from apps.schedules.services import ScheduleVersionConflict, cancel_schedule, update_schedule
from tests.factories.accounts import UserFactory
from tests.factories.shared_workspace import project_with_members

pytestmark = pytest.mark.django_db


def group_item():
    advisor = UserFactory(global_role="advisor")
    student = UserFactory()
    project = project_with_members(advisor=advisor, students=[student])
    starts_at = timezone.now() + timezone.timedelta(days=2)
    from apps.schedules.services import create_schedule

    item = create_schedule(
        actor=advisor,
        data={
            "scope": "group",
            "category": "meeting",
            "title": "Research sync",
            "all_day": False,
            "starts_at": starts_at,
            "ends_at": starts_at + timezone.timedelta(hours=1),
            "timezone": "UTC",
            "recurrence": {
                "frequency": "weekly",
                "interval": 1,
                "weekdays": [starts_at.isoweekday()],
                "until": starts_at.date() + timezone.timedelta(days=28),
            },
            "reminders": [],
            "audience": {"project_ids": [project.id], "account_ids": []},
        },
    )
    return item, advisor, student


def test_group_series_change_records_revision_and_rejects_stale_version():
    item, advisor, _ = group_item()
    admin = UserFactory(global_role="admin")
    updated = update_schedule(
        item=item,
        actor=admin,
        expected_version=1,
        change_scope="series",
        fields={"title": "Updated research sync"},
    )
    assert updated.version == 2
    assert updated.revisions.filter(change_type=ScheduleRevision.ChangeType.CHANGED).exists()
    with pytest.raises(ScheduleVersionConflict):
        update_schedule(
            item=item,
            actor=advisor,
            expected_version=1,
            change_scope="series",
            fields={"title": "Lost update"},
        )


def test_group_occurrence_cancel_is_retained_as_history():
    item, advisor, _ = group_item()
    occurrence_key = item.starts_at.isoformat()
    updated = cancel_schedule(
        item=item,
        actor=advisor,
        expected_version=1,
        change_scope="occurrence",
        occurrence_key=occurrence_key,
        reason="Unavailable",
    )
    assert updated.status == ScheduleItem.Status.ACTIVE
    assert updated.exceptions.get().status == "cancelled"
    assert updated.revisions.filter(change_type=ScheduleRevision.ChangeType.CANCELLED).exists()


def test_group_series_cancel_is_not_deleted_and_tracks_email_channel():
    item, advisor, student = group_item()
    cancelled = cancel_schedule(
        item=item,
        actor=advisor,
        expected_version=1,
        change_scope="series",
        reason="Meeting withdrawn",
    )
    assert cancelled.status == ScheduleItem.Status.CANCELLED
    assert ScheduleItem.objects.filter(pk=item.pk).exists()
    assert cancelled.notification_dispatches.filter(
        recipient=student, event_type="cancelled", channel="email"
    ).exists()
