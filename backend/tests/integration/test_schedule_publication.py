import pytest
from django.utils import timezone

from apps.notifications.models import Notification
from apps.projects.models import ProjectMembership
from apps.schedules.audience_services import reresolve_audience
from apps.schedules.models import ScheduleItem, ScheduleNotificationDispatch, ScheduleRevision
from apps.schedules.services import create_schedule
from tests.factories.accounts import UserFactory
from tests.factories.shared_workspace import project_with_members

pytestmark = pytest.mark.django_db


def test_group_publication_deduplicates_recipients_and_never_queues_email():
    advisor = UserFactory(global_role="advisor")
    first = UserFactory()
    second = UserFactory()
    project = project_with_members(advisor=advisor, students=[first, second])
    starts_at = timezone.now() + timezone.timedelta(days=1)
    item = create_schedule(
        actor=advisor,
        data={
            "scope": "group",
            "category": "meeting",
            "title": "Group methods meeting",
            "all_day": False,
            "starts_at": starts_at,
            "ends_at": starts_at + timezone.timedelta(hours=1),
            "timezone": "UTC",
            "recurrence": {"frequency": "none", "interval": 1, "weekdays": []},
            "reminders": [],
            "audience": {
                "project_ids": [project.id],
                "account_ids": [first.id],
            },
        },
    )

    assert item.scope == ScheduleItem.Scope.GROUP
    assert item.recipient_grants.count() == 2
    assert ScheduleRevision.objects.filter(schedule_item=item, revision_number=1).exists()
    notices = Notification.objects.filter(target_type="ScheduleItem", target_id=str(item.id))
    assert notices.count() == 2
    assert set(notices.values_list("delivery_policy", flat=True)) == {"in_app"}
    assert set(notices.values_list("status", flat=True)) == {"in_app_only"}
    assert (
        ScheduleNotificationDispatch.objects.filter(schedule_item=item, channel="email").count()
        == 0
    )


def test_membership_remove_and_rejoin_preserves_temporal_grant_history():
    advisor = UserFactory(global_role="advisor")
    student = UserFactory()
    project = project_with_members(advisor=advisor, students=[student])
    starts_at = timezone.now() + timezone.timedelta(days=1)
    item = create_schedule(
        actor=advisor,
        data={
            "scope": "group",
            "category": "meeting",
            "title": "Temporal membership",
            "all_day": False,
            "starts_at": starts_at,
            "ends_at": starts_at + timezone.timedelta(hours=1),
            "timezone": "UTC",
            "recurrence": {"frequency": "none", "interval": 1, "weekdays": []},
            "reminders": [],
            "audience": {"project_ids": [project.id], "account_ids": []},
        },
    )
    first = item.recipient_grants.get(recipient=student, valid_until__isnull=True)
    membership = ProjectMembership.objects.get(project=project, user=student, status="active")
    membership.status = ProjectMembership.Status.REMOVED
    membership.removed_at = timezone.now()
    membership.save()
    first.refresh_from_db()
    assert first.valid_until is not None

    ProjectMembership.objects.create(
        project=project,
        user=student,
        role=ProjectMembership.Role.STUDENT,
        status=ProjectMembership.Status.ACTIVE,
    )
    reresolve_audience(item)
    grants = list(item.recipient_grants.filter(recipient=student).order_by("valid_from"))
    assert len(grants) == 2
    assert grants[0].valid_until is not None
    assert grants[1].valid_until is None
