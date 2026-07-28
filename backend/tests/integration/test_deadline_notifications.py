import pytest
from django.utils import timezone
from django_celery_beat.models import PeriodicTask

from apps.notifications.tasks import create_deadline_reminders, ensure_periodic_notification_tasks
from apps.projects.models import ProjectMembership, ResearchProject
from apps.tasks.models import Task
from tests.factories.accounts import UserFactory


@pytest.mark.django_db
def test_deadline_reminder_records_are_created_for_assignees():
    advisor = UserFactory(global_role="advisor")
    student = UserFactory(global_role="student")
    project = ResearchProject.objects.create(title="A", advisor=advisor)
    ProjectMembership.objects.create(project=project, user=advisor, role="advisor")
    ProjectMembership.objects.create(project=project, user=student, role="student")
    task = Task.objects.create(
        project=project,
        title="Due soon",
        assignee=student,
        deadline_at=timezone.now() + timezone.timedelta(days=1),
        created_by=advisor,
    )

    created = create_deadline_reminders()

    assert created >= 1
    assert project.notifications.filter(target_id=f"{task.id}:1d", recipient=student).exists()


@pytest.mark.django_db
def test_project_deadline_reminders_and_periodic_schedule_are_created():
    advisor = UserFactory(global_role="advisor")
    student = UserFactory(global_role="student")
    project = ResearchProject.objects.create(
        title="Project deadline",
        advisor=advisor,
        ends_on=timezone.localdate() + timezone.timedelta(days=7),
    )
    ProjectMembership.objects.create(project=project, user=advisor, role="advisor")
    ProjectMembership.objects.create(project=project, user=student, role="student")

    created = create_deadline_reminders()
    schedule_created = ensure_periodic_notification_tasks()

    assert created == 2
    assert project.notifications.filter(
        target_type="ResearchProject", target_id=f"{project.id}:due_soon", recipient=advisor
    ).exists()
    assert project.notifications.filter(
        target_type="ResearchProject", target_id=f"{project.id}:due_soon", recipient=student
    ).exists()
    assert schedule_created == 7
    assert PeriodicTask.objects.filter(
        name="GradSync deadline reminders",
        interval__every=5,
        interval__period="minutes",
        enabled=True,
    ).exists()
    assert PeriodicTask.objects.filter(
        name="GradSync schedule reminders",
        interval__every=5,
        interval__period="minutes",
        enabled=True,
    ).exists()
