from datetime import timedelta

import pytest
from django.utils import timezone

from apps.schedules.models import ScheduleItem, ScheduleRecipientGrant
from apps.schedules.permissions import (
    can_manage_group_item,
    can_view_schedule_item,
    eligible_recipient_accounts,
)
from apps.schedules.projection_services import authored_schedule_occurrences
from tests.factories.accounts import UserFactory
from tests.factories.shared_workspace import project_with_members

pytestmark = pytest.mark.django_db


def test_admin_cannot_view_another_users_private_schedule():
    owner = UserFactory()
    admin = UserFactory(global_role="admin")
    item = ScheduleItem.objects.create(
        owner=owner,
        organizer=owner,
        title="Private",
        starts_at=timezone.now(),
        ends_at=timezone.now() + timedelta(hours=1),
    )

    assert can_view_schedule_item(owner, item)
    assert not can_view_schedule_item(admin, item)
    window_start = item.starts_at - timedelta(minutes=1)
    window_end = item.ends_at + timedelta(minutes=1)
    assert authored_schedule_occurrences(admin, window_start, window_end) == []


def test_group_recipient_visibility_obeys_grant_interval():
    advisor = UserFactory(global_role="advisor")
    recipient = UserFactory()
    item = ScheduleItem.objects.create(
        owner=advisor,
        organizer=advisor,
        scope="group",
        title="Group",
        starts_at=timezone.now(),
        ends_at=timezone.now() + timedelta(hours=1),
        published_at=timezone.now(),
    )
    starts = timezone.now()
    ScheduleRecipientGrant.objects.create(
        schedule_item=item,
        recipient=recipient,
        valid_from=starts,
        valid_until=starts + timedelta(days=1),
        source_types=["account"],
    )

    assert can_view_schedule_item(recipient, item, occurrence_at=starts + timedelta(hours=1))
    assert not can_view_schedule_item(recipient, item, occurrence_at=starts + timedelta(days=2))
    assert can_manage_group_item(advisor, item)


def test_advisor_recipient_options_are_limited_to_managed_project_members():
    advisor = UserFactory(global_role="advisor")
    managed_student = UserFactory()
    unrelated_student = UserFactory()
    project_with_members(advisor=advisor, students=[managed_student])

    assert set(eligible_recipient_accounts(advisor)) == {managed_student, advisor}
    assert unrelated_student not in eligible_recipient_accounts(advisor)
