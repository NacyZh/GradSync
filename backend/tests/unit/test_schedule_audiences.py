import pytest
from django.core.exceptions import ValidationError
from django.utils import timezone

from apps.schedules.audience_services import resolve_audience, searchable_accounts
from apps.schedules.models import ScheduleRecipientGrant
from tests.factories.accounts import UserFactory
from tests.factories.shared_workspace import project_with_members

pytestmark = pytest.mark.django_db


def test_advisor_account_search_is_limited_to_managed_project_members():
    advisor = UserFactory(global_role="advisor")
    student = UserFactory(name="Visible Student")
    unrelated = UserFactory(name="Unrelated Student")
    project_with_members(advisor=advisor, students=[student])

    assert student in searchable_accounts(advisor, "Visible")
    assert unrelated not in searchable_accounts(advisor, "Student")


def test_overlapping_project_and_account_audience_creates_one_open_grant(schedule_factory):
    advisor = UserFactory(global_role="advisor")
    student = UserFactory()
    project = project_with_members(advisor=advisor, students=[student])
    item = schedule_factory(
        owner=advisor,
        organizer=advisor,
        scope="group",
        published_at=timezone.now(),
    )

    summary = resolve_audience(
        actor=advisor,
        item=item,
        project_ids=[project.id],
        account_ids=[student.id],
    )

    assert summary["resolvedRecipientCount"] == 1
    assert ScheduleRecipientGrant.objects.filter(schedule_item=item, recipient=student).count() == 1


def test_empty_or_unrelated_audience_is_rejected(schedule_factory):
    advisor = UserFactory(global_role="advisor")
    item = schedule_factory(
        owner=advisor,
        organizer=advisor,
        scope="group",
        published_at=timezone.now(),
    )
    unrelated = UserFactory()
    with pytest.raises(ValidationError):
        resolve_audience(actor=advisor, item=item, project_ids=[], account_ids=[])
    with pytest.raises(ValidationError):
        resolve_audience(actor=advisor, item=item, project_ids=[], account_ids=[unrelated.id])
