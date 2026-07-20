from celery import shared_task
from celery.utils.log import get_task_logger
from django.conf import settings
from django.core.mail import send_mail
from django.utils import timezone
from django_celery_beat.models import IntervalSchedule, PeriodicTask

from apps.projects.models import ResearchProject
from apps.tasks.models import Task

from .models import Notification
from .services import (
    mark_notification_attempt_failed,
    mark_notification_status,
    notification_is_deliverable,
)

logger = get_task_logger(__name__)


def _deadline_window(now, deadline):
    if not deadline:
        return None
    delta = deadline - now
    if timezone.timedelta(hours=23) <= delta <= timezone.timedelta(days=1, hours=1):
        return "1d"
    if timezone.timedelta(days=6, hours=23) <= delta <= timezone.timedelta(days=7, hours=1):
        return "7d"
    if timezone.timedelta() <= delta <= timezone.timedelta(days=7):
        return "due_soon"
    return None


def create_deadline_reminders() -> int:
    now = timezone.now()
    created = 0
    tasks = Task.objects.filter(
        project__status="active",
        deadline_at__isnull=False,
        deadline_at__lte=now + timezone.timedelta(days=7, hours=1),
    ).exclude(status__in=["completed", "cancelled"])
    for task in tasks.select_related("project", "assignee").prefetch_related("assignees"):
        recipients = list(task.assignees.all())
        if not recipients and task.assignee_id:
            recipients = [task.assignee]
        if not recipients:
            continue
        window = _deadline_window(now, task.deadline_at)
        if not window:
            continue
        for recipient in recipients:
            _, was_created = Notification.objects.get_or_create(
                project=task.project,
                recipient=recipient,
                event_type=Notification.EventType.APPROACHING_DEADLINE,
                target_type="Task",
                target_id=f"{task.id}:{window}",
                defaults={
                    "subject": f"Deadline approaching ({window}): {task.title}",
                    "action_path": f"/projects/{task.project_id}/tasks/{task.id}",
                    "eligible_at": now,
                },
            )
            created += int(was_created)
    projects = ResearchProject.objects.filter(status="active", ends_on__isnull=False)
    for project in projects.prefetch_related("memberships__user"):
        deadline = timezone.datetime.combine(
            project.ends_on, timezone.datetime.min.time(), tzinfo=timezone.get_current_timezone()
        )
        window = _deadline_window(now, deadline)
        if not window:
            continue
        for membership in project.memberships.filter(status="active"):
            _, was_created = Notification.objects.get_or_create(
                project=project,
                recipient=membership.user,
                event_type=Notification.EventType.APPROACHING_DEADLINE,
                target_type="ResearchProject",
                target_id=f"{project.id}:{window}",
                defaults={
                    "subject": f"Project deadline approaching ({window}): {project.title}",
                    "action_path": f"/projects/{project.id}",
                    "eligible_at": now,
                },
            )
            created += int(was_created)
    return created


def create_pending_review_reminders() -> int:
    from apps.submissions.models import WeeklyProgressReport

    now = timezone.now()
    created = 0
    reports = WeeklyProgressReport.objects.filter(
        project__status="active", review_status="pending_review"
    )
    for target, target_type, submitted_at in [
        *[(report, "WeeklyProgressReport", report.submitted_at) for report in reports],
    ]:
        if submitted_at > now - timezone.timedelta(days=3):
            continue
        for membership in target.project.memberships.filter(
            role__in=["advisor", "reviewer"], status="active"
        ):
            _, was_created = Notification.objects.get_or_create(
                project=target.project,
                recipient=membership.user,
                event_type=Notification.EventType.PENDING_REVIEW,
                target_type=target_type,
                target_id=str(target.id),
                defaults={
                    "subject": f"Pending review: {target_type} {target.id}",
                    "action_path": f"/projects/{target.project_id}/reviews",
                    "eligible_at": now,
                },
            )
            created += int(was_created)
    return created


def deliver_due_notifications(limit: int = 100) -> int:
    now = timezone.now()
    delivered = 0
    notifications = Notification.objects.filter(
        status__in=[Notification.Status.PENDING, Notification.Status.RETRY_NEEDED],
        delivery_policy=Notification.DeliveryPolicy.IN_APP_EMAIL,
        eligible_at__lte=now,
    ).select_related("recipient", "project", "sender")[:limit]
    for notification in notifications:
        if not notification_is_deliverable(notification):
            mark_notification_status(
                notification,
                Notification.Status.SKIPPED,
                "Recipient is no longer an active project member",
            )
            _sync_schedule_dispatch(notification, "skipped")
            continue
        mark_notification_status(notification, Notification.Status.QUEUED)
        project_label = notification.project.title if notification.project_id else "GradSync"
        action_path = notification.action_path
        if not action_path and notification.project_id:
            action_path = f"/projects/{notification.project_id}"
        body = (
            f"Project: {project_label}\n"
            f"Record: {notification.target_type} {notification.target_id}\n"
            f"Action: {notification.subject}\n"
            f"Sender: {notification.sender.name if notification.sender else 'GradSync'}\n"
            f"Path: {action_path or '/'}"
        )
        try:
            send_mail(
                notification.subject,
                body,
                settings.DEFAULT_FROM_EMAIL,
                [notification.recipient_email or notification.recipient.email],
            )
        except (
            Exception
        ) as exc:  # pragma: no cover - exercised by integration error paths in real mail setup
            mark_notification_attempt_failed(notification, exc)
            _sync_schedule_dispatch(notification, "failed")
            continue
        mark_notification_status(notification, Notification.Status.SENT)
        _sync_schedule_dispatch(notification, "created")
        delivered += 1
    return delivered


def _sync_schedule_dispatch(notification, status):
    if notification.target_type != "ScheduleItem":
        return
    from apps.schedules.models import ScheduleNotificationDispatch

    ScheduleNotificationDispatch.objects.filter(
        notification=notification,
        channel=ScheduleNotificationDispatch.Channel.EMAIL,
    ).update(status=status, updated_at=timezone.now())


@shared_task(queue="notifications")
def create_deadline_reminders_task() -> int:
    return create_deadline_reminders()


@shared_task(queue="notifications")
def create_pending_review_reminders_task() -> int:
    return create_pending_review_reminders()


@shared_task(queue="notifications")
def create_schedule_reminders_task() -> int:
    from apps.schedules.reminder_services import create_due_schedule_reminders

    created = create_due_schedule_reminders()
    logger.info("schedule_reminder_scan created=%s", created)
    return created


@shared_task(
    bind=True,
    queue="notifications",
    autoretry_for=(ConnectionError, TimeoutError),
    retry_backoff=True,
    retry_jitter=True,
    retry_kwargs={"max_retries": 5},
)
def deliver_due_notifications_task(self, limit: int = 100) -> int:
    return deliver_due_notifications(limit=limit)


def ensure_periodic_notification_tasks() -> int:
    schedule, _ = IntervalSchedule.objects.get_or_create(every=5, period=IntervalSchedule.MINUTES)
    created = 0
    for name, task in [
        ("GradSync deadline reminders", "apps.notifications.tasks.create_deadline_reminders_task"),
        (
            "GradSync pending review reminders",
            "apps.notifications.tasks.create_pending_review_reminders_task",
        ),
        (
            "GradSync notification delivery",
            "apps.notifications.tasks.deliver_due_notifications_task",
        ),
        (
            "GradSync schedule reminders",
            "apps.notifications.tasks.create_schedule_reminders_task",
        ),
    ]:
        _, was_created = PeriodicTask.objects.update_or_create(
            name=name,
            defaults={"interval": schedule, "task": task, "enabled": True},
        )
        created += int(was_created)
    return created
