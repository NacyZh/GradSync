import pytest
from django.utils import timezone

from apps.notifications.models import Notification
from apps.schedules.models import ScheduleNotificationDispatch, ScheduleReminder
from apps.schedules.reminder_services import create_due_schedule_reminders
from tests.factories.schedules import ScheduleItemFactory

pytestmark = pytest.mark.django_db


def test_due_reminder_claims_each_channel_once():
    now = timezone.now().replace(second=0, microsecond=0)
    item = ScheduleItemFactory(
        starts_at=now + timezone.timedelta(minutes=30),
        ends_at=now + timezone.timedelta(minutes=90),
    )
    ScheduleReminder.objects.create(schedule_item=item, offset_minutes=30)

    assert create_due_schedule_reminders(now=now) == 1
    assert create_due_schedule_reminders(now=now) == 0
    assert (
        Notification.objects.filter(target_type="ScheduleItem", target_id=str(item.id)).count() == 1
    )
    assert set(
        ScheduleNotificationDispatch.objects.filter(schedule_item=item).values_list(
            "channel", flat=True
        )
    ) == {"in_app", "email"}


def test_cancelled_and_completed_items_do_not_generate_reminders():
    now = timezone.now().replace(second=0, microsecond=0)
    for status in ("cancelled", "completed"):
        item = ScheduleItemFactory(
            status=status,
            cancelled_at=now if status == "cancelled" else None,
            starts_at=now + timezone.timedelta(minutes=15),
            ends_at=now + timezone.timedelta(minutes=45),
        )
        ScheduleReminder.objects.create(schedule_item=item, offset_minutes=15)
    assert create_due_schedule_reminders(now=now) == 0


@pytest.mark.parametrize("offset", ScheduleReminder.ALLOWED_OFFSETS)
def test_each_supported_offset_is_claimed(offset):
    now = timezone.now().replace(second=0, microsecond=0)
    item = ScheduleItemFactory(
        starts_at=now + timezone.timedelta(minutes=offset),
        ends_at=now + timezone.timedelta(minutes=offset + 30),
    )
    ScheduleReminder.objects.create(schedule_item=item, offset_minutes=offset)
    assert create_due_schedule_reminders(now=now) == 1


def test_all_day_reminder_uses_local_midnight():
    local_midnight = timezone.now().replace(hour=0, minute=0, second=0, microsecond=0)
    item = ScheduleItemFactory(
        all_day=True,
        starts_at=None,
        ends_at=None,
        starts_on=local_midnight.date() + timezone.timedelta(days=1),
        ends_on=local_midnight.date() + timezone.timedelta(days=2),
    )
    ScheduleReminder.objects.create(schedule_item=item, offset_minutes=1440)
    assert create_due_schedule_reminders(now=local_midnight) == 1
