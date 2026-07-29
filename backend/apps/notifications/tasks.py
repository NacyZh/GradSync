from celery import shared_task
from celery.utils.log import get_task_logger
from django.conf import settings
from django.core.mail import send_mail
from django.db import models
from django.utils import timezone
from django_celery_beat.models import IntervalSchedule, PeriodicTask

from apps.projects.models import ResearchProject
from apps.tasks.models import Task

from .models import Notification, NotificationDeliveryAttempt
from .outcome_services import (
    expire_notification,
    mark_notification_unavailable,
    reconcile_authoritative_action,
)
from .policy_services import effective_project_policy
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
        delivery_policy__in=[
            Notification.DeliveryPolicy.IN_APP_EMAIL,
            Notification.DeliveryPolicy.EMAIL_ONLY,
        ],
        eligible_at__lte=now,
    ).select_related("recipient", "project", "sender")[:limit]
    for notification in notifications:
        if not notification_is_deliverable(notification):
            reason = (
                "Verification code is expired, revoked, or superseded"
                if notification.event_type == Notification.EventType.VERIFICATION_CODE
                else "Recipient is no longer an active project member"
            )
            mark_notification_status(
                notification,
                Notification.Status.SKIPPED,
                reason,
            )
            _sync_schedule_dispatch(notification, "skipped")
            if notification.active_follow_up:
                mark_notification_unavailable(notification)
            continue
        attempt_number = notification.retry_count + 1
        NotificationDeliveryAttempt.objects.get_or_create(
            notification=notification,
            channel=NotificationDeliveryAttempt.Channel.EMAIL,
            attempt_number=attempt_number,
            defaults={
                "eligible_at": notification.eligible_at,
                "idempotency_key": (f"notification:{notification.pk}:email:{attempt_number}"),
            },
        )
        mark_notification_status(notification, Notification.Status.QUEUED)
        body = _notification_email_body(notification)
        try:
            delivered_count = send_mail(
                notification.subject,
                body,
                settings.DEFAULT_FROM_EMAIL,
                [notification.recipient_email or notification.recipient.email],
                fail_silently=False,
            )
            if delivered_count != 1:
                raise RuntimeError("SMTP backend did not accept the notification email.")
        except (
            Exception
        ) as exc:  # pragma: no cover - exercised by integration error paths in real mail setup
            mark_notification_attempt_failed(
                notification,
                exc,
                retry_needed=notification.retry_count < 4,
            )
            _sync_schedule_dispatch(notification, "failed")
            continue
        mark_notification_status(notification, Notification.Status.SENT)
        _sync_schedule_dispatch(notification, "created")
        delivered += 1
    return delivered


def _notification_email_body(notification: Notification) -> str:
    if notification.event_type == Notification.EventType.VERIFICATION_CODE:
        from apps.accounts.models import EmailVerificationCode

        verification = EmailVerificationCode.objects.get(pk=notification.target_id)
        return (
            f"Your GradSync verification code is {verification.plain_code}.\n"
            f"It expires in {settings.EMAIL_VERIFICATION_CODE_TTL_MINUTES} minutes."
        )
    project_label = notification.project.title if notification.project_id else "GradSync"
    action_path = notification.action_path
    if not action_path and notification.project_id:
        action_path = f"/projects/{notification.project_id}"
    return (
        f"Project: {project_label}\n"
        f"Record: {notification.target_type} {notification.target_id}\n"
        f"Action: {notification.subject}\n"
        f"Sender: {notification.sender.name if notification.sender else 'GradSync'}\n"
        f"Path: {action_path or '/'}"
    )


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


def process_actionable_notification_followups(limit: int | None = None) -> int:
    now = timezone.now()
    limit = max(
        1,
        min(
            limit or settings.GRADSYNC_EXECUTION_JOB_BATCH_SIZE,
            settings.GRADSYNC_EXECUTION_JOB_BATCH_SIZE,
        ),
    )
    processed = 0
    notifications = (
        Notification.objects.filter(
            active_follow_up=True,
            outcome_state=Notification.OutcomeState.PENDING,
        )
        .select_related("project", "recipient")
        .order_by("due_at", "id")[:limit]
    )
    for notification in notifications:
        reconciled = reconcile_authoritative_action(
            notification=notification,
            event_type="scheduled.reconcile",
            event_id=notification.target_id,
        )
        if reconciled.outcome_state == Notification.OutcomeState.COMPLETED:
            processed += 1
            continue
        if notification.expires_at and notification.expires_at <= now:
            expire_notification(notification)
            processed += 1
            continue
        if not notification.due_at:
            continue
        policy = (
            effective_project_policy(notification.project)
            if notification.project_id
            else {
                "reminder_lead_minutes": settings.GRADSYNC_NOTIFICATION_REMINDER_LEAD_MINUTES,
                "escalation_delay_minutes": settings.GRADSYNC_NOTIFICATION_ESCALATION_DELAY_MINUTES,
                "repeat_interval_minutes": settings.GRADSYNC_NOTIFICATION_REPEAT_INTERVAL_MINUTES,
                "max_reminders": settings.GRADSYNC_NOTIFICATION_MAX_REMINDERS,
            }
        )
        reminder_due = notification.due_at - timezone.timedelta(
            minutes=policy["reminder_lead_minutes"]
        )
        repeat_due = (
            notification.last_reminded_at is None
            or notification.last_reminded_at
            + timezone.timedelta(minutes=policy["repeat_interval_minutes"])
            <= now
        )
        if (
            reminder_due <= now
            and repeat_due
            and notification.reminder_count < policy["max_reminders"]
        ):
            notification.reminder_count += 1
            notification.last_reminded_at = now
            notification.save(update_fields=["reminder_count", "last_reminded_at"])
            processed += 1
        escalation_due = notification.due_at + timezone.timedelta(
            minutes=policy["escalation_delay_minutes"]
        )
        if escalation_due <= now and notification.escalation_level == 0:
            notification.escalation_level = 1
            notification.last_escalated_at = now
            notification.save(update_fields=["escalation_level", "last_escalated_at"])
            processed += 1
    return processed


@shared_task(queue="notifications")
def process_actionable_notification_followups_task(limit: int | None = None) -> int:
    return process_actionable_notification_followups(limit=limit)


@shared_task(queue="notifications")
def maintain_reporting_periods_task() -> int:
    from apps.submissions.report_period_services import (
        close_due_reporting_periods,
        open_current_reporting_periods,
    )

    opened = open_current_reporting_periods()
    closed = close_due_reporting_periods()
    logger.info("reporting_period_maintenance opened=%s closed=%s", opened, closed)
    return opened + closed


def create_risk_review_reminders(limit: int | None = None) -> int:
    from apps.projects.models import RiskRecord

    current = timezone.localdate()
    maximum = max(
        1,
        min(
            limit or settings.GRADSYNC_EXECUTION_JOB_BATCH_SIZE,
            settings.GRADSYNC_EXECUTION_JOB_BATCH_SIZE,
        ),
    )
    rows = (
        RiskRecord.objects.filter(
            project__status="active",
            state__in=[
                RiskRecord.State.RAISED,
                RiskRecord.State.OPEN,
                RiskRecord.State.MITIGATING,
            ],
        )
        .filter(models.Q(severity=RiskRecord.Level.HIGH) | models.Q(review_date__lte=current))
        .select_related("project", "owner")[:maximum]
    )
    created = 0
    for risk in rows:
        recipients = (
            [risk.owner]
            if risk.owner_id
            else [
                membership.user
                for membership in risk.project.memberships.filter(
                    role__in=["advisor", "co_advisor"], status="active"
                ).select_related("user")
            ]
        )
        for recipient in recipients:
            if recipient is None:
                continue
            _, was_created = Notification.objects.get_or_create(
                recipient=recipient,
                dedupe_key=f"risk:{risk.id}:active-review",
                active_follow_up=True,
                defaults={
                    "project": risk.project,
                    "event_type": Notification.EventType.APPROACHING_DEADLINE,
                    "target_type": "RiskRecord",
                    "target_id": str(risk.id),
                    "subject": f"Risk review required: {risk.title}",
                    "action_path": f"/projects/{risk.project_id}/execution?tab=risks",
                    "eligible_at": timezone.now(),
                    "category": Notification.Category.RISK,
                    "requirement_type": Notification.RequirementType.ACTION,
                    "outcome_state": Notification.OutcomeState.PENDING,
                    "due_at": (
                        timezone.make_aware(
                            timezone.datetime.combine(
                                risk.review_date, timezone.datetime.max.time()
                            )
                        )
                        if risk.review_date
                        else timezone.now()
                    ),
                },
            )
            created += int(was_created)
    return created


@shared_task(queue="notifications")
def create_risk_review_reminders_task() -> int:
    return create_risk_review_reminders()


@shared_task(queue="notifications")
def reconcile_resource_operations_task() -> int:
    from apps.resources.services import reconcile_resource_operation_alerts

    updated = reconcile_resource_operation_alerts()
    logger.info("resource_operation_scan alerts_created=%s", updated)
    return updated


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
        (
            "GradSync actionable notification follow-ups",
            "apps.notifications.tasks.process_actionable_notification_followups_task",
        ),
        (
            "GradSync reporting period maintenance",
            "apps.notifications.tasks.maintain_reporting_periods_task",
        ),
        (
            "GradSync risk review reminders",
            "apps.notifications.tasks.create_risk_review_reminders_task",
        ),
        (
            "GradSync resource operation alerts",
            "apps.notifications.tasks.reconcile_resource_operations_task",
        ),
    ]:
        _, was_created = PeriodicTask.objects.update_or_create(
            name=name,
            defaults={"interval": schedule, "task": task, "enabled": True},
        )
        created += int(was_created)
    return created
