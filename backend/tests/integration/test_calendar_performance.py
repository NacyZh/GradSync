import time
from datetime import timedelta

import pytest
from django.contrib.auth import get_user_model
from django.utils import timezone

from apps.projects.models import ProjectMembership
from apps.schedules.models import (
    ScheduleAudience,
    ScheduleRecipientGrant,
    ScheduleReminder,
)
from apps.schedules.reminder_services import create_due_schedule_reminders
from apps.tasks.models import Task
from tests.factories.accounts import UserFactory
from tests.factories.schedules import ScheduleItemFactory
from tests.factories.shared_workspace import project_with_members
from tests.helpers import authenticate


@pytest.mark.django_db
def test_calendar_returns_ten_thousand_authorized_occurrences_within_budget(
    api_client, django_assert_max_num_queries
):
    advisor = UserFactory(global_role="advisor")
    project = project_with_members(advisor=advisor)
    user_model = get_user_model()
    accounts = user_model.objects.bulk_create(
        [
            user_model(
                email=f"calendar-user-{index}@example.com",
                name=f"Calendar User {index}",
                global_role="student",
                status="active",
            )
            for index in range(499)
        ]
    )
    ProjectMembership.objects.bulk_create(
        [
            ProjectMembership(project=project, user=account, role="student", status="active")
            for account in accounts
        ]
    )
    now = timezone.now()
    Task.objects.bulk_create(
        [
            Task(
                project=project,
                title=f"Scale task {index}",
                created_by=advisor,
                deadline_at=now + timedelta(days=index % 30, minutes=index % 1440),
            )
            for index in range(10_000)
        ]
    )

    started = time.monotonic()
    with django_assert_max_num_queries(14):
        response = authenticate(api_client, advisor).get(
            "/api/calendar/occurrences/",
            {
                "startsAt": (now - timedelta(minutes=1)).isoformat(),
                "endsAt": (now + timedelta(days=31)).isoformat(),
                "sources": "task",
            },
        )
    elapsed = time.monotonic() - started

    assert response.status_code == 200
    assert len(response.json()["results"]) == 10_000
    assert elapsed < 2.0


@pytest.mark.django_db
def test_five_hundred_recipient_reminder_batch_completes_within_worker_window():
    advisor = UserFactory(global_role="advisor")
    project = project_with_members(advisor=advisor)
    user_model = get_user_model()
    recipients = user_model.objects.bulk_create(
        [
            user_model(
                email=f"reminder-user-{index}@example.com",
                name=f"Reminder User {index}",
                global_role="student",
                status="active",
            )
            for index in range(500)
        ]
    )
    ProjectMembership.objects.bulk_create(
        [
            ProjectMembership(project=project, user=user, role="student", status="active")
            for user in recipients
        ]
    )
    now = timezone.now().replace(second=0, microsecond=0)
    item = ScheduleItemFactory(
        owner=advisor,
        organizer=advisor,
        scope="group",
        published_at=now,
        starts_at=now + timedelta(minutes=30),
        ends_at=now + timedelta(minutes=60),
    )
    ScheduleAudience.objects.create(
        schedule_item=item,
        scope_type="project",
        project=project,
        created_by=advisor,
    )
    ScheduleRecipientGrant.objects.bulk_create(
        [
            ScheduleRecipientGrant(
                schedule_item=item,
                recipient=user,
                valid_from=now - timedelta(minutes=1),
                source_types=["project"],
                source_project_ids=[project.id],
            )
            for user in recipients
        ]
    )
    ScheduleReminder.objects.create(schedule_item=item, offset_minutes=30)

    started = time.monotonic()
    created = create_due_schedule_reminders(now=now, limit=500)
    elapsed = time.monotonic() - started

    assert created == 500
    assert item.notification_dispatches.count() == 1000
    assert elapsed < 10.0
