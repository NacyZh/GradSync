import re

from django.db.models import DateTimeField, OuterRef, Q, Subquery
from django.utils import timezone

from .models import Notification, NotificationDeliveryAttempt, NotificationReadReceipt

RETRY_NEEDED_STATUSES = {Notification.Status.FAILED, Notification.Status.RETRY_NEEDED}

_SECRET_PATTERNS = (
    re.compile(r"(?i)(password|passwd|pwd|secret|token|api[_-]?key)=([^\s,;]+)"),
    re.compile(r"(?i)(verification\s*code|code)\s*[:=]\s*([0-9A-Za-z_-]{4,})"),
)


def mask_notification_failure_reason(reason: str) -> str:
    masked = str(reason or "")
    for pattern in _SECRET_PATTERNS:
        masked = pattern.sub(lambda match: f"{match.group(1)}=[masked]", masked)
    return masked[:500]


def notification_needs_retry(notification: Notification) -> bool:
    return notification.status in RETRY_NEEDED_STATUSES


def mark_notification_status(notification: Notification, status: str, failure_reason: str = ""):
    now = timezone.now()
    notification.status = status
    if status == Notification.Status.QUEUED:
        notification.queued_at = now
    elif status == Notification.Status.SENT:
        notification.sent_at = now
        notification.failure_reason = ""
    if failure_reason:
        notification.failure_reason = mask_notification_failure_reason(failure_reason)
    notification.save(update_fields=["status", "queued_at", "sent_at", "failure_reason"])
    attempt = notification.delivery_attempts.filter(
        channel=NotificationDeliveryAttempt.Channel.EMAIL,
        attempt_number=max(notification.retry_count + 1, 1),
    ).first()
    if attempt:
        attempt.state = {
            Notification.Status.QUEUED: NotificationDeliveryAttempt.State.QUEUED,
            Notification.Status.SENT: NotificationDeliveryAttempt.State.SENT,
            Notification.Status.SKIPPED: NotificationDeliveryAttempt.State.SKIPPED,
        }.get(status, attempt.state)
        if status in {Notification.Status.SENT, Notification.Status.SKIPPED}:
            attempt.completed_at = now
        attempt.attempted_at = attempt.attempted_at or now
        attempt.failure_reason_masked = mask_notification_failure_reason(failure_reason)
        attempt.save()
    return notification


def mark_notification_attempt_failed(
    notification: Notification,
    exc: Exception | str,
    *,
    retry_needed: bool = True,
) -> Notification:
    notification.status = (
        Notification.Status.RETRY_NEEDED if retry_needed else Notification.Status.FAILED
    )
    notification.failure_reason = mask_notification_failure_reason(str(exc))
    notification.last_attempt_at = timezone.now()
    notification.retry_count += 1
    notification.eligible_at = notification.last_attempt_at + timezone.timedelta(minutes=5)
    notification.save(
        update_fields=[
            "status",
            "failure_reason",
            "last_attempt_at",
            "retry_count",
            "eligible_at",
        ]
    )
    attempt, _ = NotificationDeliveryAttempt.objects.get_or_create(
        notification=notification,
        channel=NotificationDeliveryAttempt.Channel.EMAIL,
        attempt_number=notification.retry_count,
        defaults={
            "eligible_at": notification.last_attempt_at,
            "idempotency_key": (
                f"notification:{notification.pk}:email:{notification.retry_count}"
            ),
        },
    )
    attempt.state = NotificationDeliveryAttempt.State.FAILED
    attempt.attempted_at = notification.last_attempt_at
    attempt.completed_at = notification.last_attempt_at
    attempt.failure_code = exc.__class__.__name__ if isinstance(exc, Exception) else "delivery"
    attempt.failure_reason_masked = notification.failure_reason
    attempt.save()
    return notification


def enqueue_notification(
    *,
    recipient,
    event_type: str,
    target_type: str,
    target_id: str,
    subject: str,
    project=None,
    sender=None,
    action_path: str = "",
    eligible_at=None,
    status: str = Notification.Status.PENDING,
    failure_reason: str = "",
    delivery_policy: str = Notification.DeliveryPolicy.IN_APP_EMAIL,
    category: str | None = None,
    requirement_type: str = Notification.RequirementType.INFORMATIONAL,
    outcome_state: str | None = None,
    due_at=None,
    expires_at=None,
    dedupe_key: str = "",
    active_follow_up: bool = False,
) -> Notification:
    if delivery_policy == Notification.DeliveryPolicy.IN_APP:
        status = Notification.Status.IN_APP_ONLY
    if category is None:
        if event_type in {
            Notification.EventType.VERIFICATION_CODE,
            Notification.EventType.PASSWORD_RECOVERY,
            Notification.EventType.EMAIL_CHANGE_SECURITY,
        }:
            category = Notification.Category.SECURITY
        elif (
            event_type.startswith("schedule_")
            or event_type == Notification.EventType.BOOKING_CHANGED
        ):
            category = Notification.Category.SCHEDULE
        elif event_type in {
            Notification.EventType.NEW_SUBMISSION,
            Notification.EventType.PENDING_REVIEW,
            Notification.EventType.TEACHER_FEEDBACK,
            Notification.EventType.TEACHER_FEEDBACK_AVAILABLE,
        }:
            category = Notification.Category.REPORT
        else:
            category = Notification.Category.PROJECT
    if outcome_state is None:
        outcome_state = (
            Notification.OutcomeState.NOT_REQUIRED
            if requirement_type == Notification.RequirementType.INFORMATIONAL
            else Notification.OutcomeState.PENDING
        )
    notification = Notification.objects.create(
        project=project,
        recipient=recipient,
        recipient_email=getattr(recipient, "email", ""),
        sender=sender,
        event_type=event_type,
        target_type=target_type,
        target_id=str(target_id),
        subject=subject,
        action_path=action_path,
        status=status,
        delivery_policy=delivery_policy,
        eligible_at=eligible_at or timezone.now(),
        failure_reason=mask_notification_failure_reason(failure_reason),
        category=category,
        requirement_type=requirement_type,
        outcome_state=outcome_state,
        due_at=due_at,
        expires_at=expires_at,
        dedupe_key=dedupe_key,
        active_follow_up=active_follow_up,
    )
    if delivery_policy != Notification.DeliveryPolicy.EMAIL_ONLY:
        NotificationDeliveryAttempt.objects.create(
            notification=notification,
            channel=NotificationDeliveryAttempt.Channel.IN_APP,
            attempt_number=1,
            state=NotificationDeliveryAttempt.State.SENT,
            eligible_at=notification.eligible_at,
            attempted_at=notification.created_at,
            completed_at=notification.created_at,
            idempotency_key=f"notification:{notification.pk}:in_app:1",
        )
    if delivery_policy != Notification.DeliveryPolicy.IN_APP:
        from .policy_services import email_enabled_for, quiet_hours_eligible_at

        eligible = (
            notification.eligible_at
            if category == Notification.Category.SECURITY
            else quiet_hours_eligible_at(recipient, notification.eligible_at)
        )
        email_enabled = email_enabled_for(recipient, category)
        NotificationDeliveryAttempt.objects.create(
            notification=notification,
            channel=NotificationDeliveryAttempt.Channel.EMAIL,
            attempt_number=1,
            state=(
                NotificationDeliveryAttempt.State.PENDING
                if email_enabled
                else NotificationDeliveryAttempt.State.SKIPPED
            ),
            eligible_at=eligible,
            completed_at=None if email_enabled else timezone.now(),
            failure_code="" if email_enabled else "preference_disabled",
            idempotency_key=f"notification:{notification.pk}:email:1",
        )
        if email_enabled and eligible > notification.eligible_at:
            notification.eligible_at = eligible
            notification.save(update_fields=["eligible_at"])
        elif not email_enabled:
            notification.status = Notification.Status.IN_APP_ONLY
            notification.save(update_fields=["status"])
    return notification


def notification_is_deliverable(notification: Notification) -> bool:
    if notification.event_type == Notification.EventType.VERIFICATION_CODE:
        from apps.accounts.models import EmailVerificationCode

        verification = EmailVerificationCode.objects.filter(pk=notification.target_id).first()
        return bool(
            verification
            and verification.email == notification.recipient_email
            and verification.is_usable()
        )
    if notification.target_type == "ScheduleItem":
        from apps.schedules.models import ScheduleItem

        item = ScheduleItem.objects.filter(pk=notification.target_id).first()
        if not item or item.status == ScheduleItem.Status.COMPLETED:
            return False
        if item.scope == ScheduleItem.Scope.PERSONAL:
            return item.owner_id == notification.recipient_id
        return item.recipient_grants.filter(
            recipient=notification.recipient, valid_until__isnull=True
        ).exists()
    if notification.project_id is None:
        return True
    return notification.project.memberships.filter(
        user=notification.recipient, status="active"
    ).exists()


def notifications_visible_to(user, *, project=None):
    viewer_receipt = NotificationReadReceipt.objects.filter(
        notification_id=OuterRef("pk"), viewer=user
    ).values("viewed_at")[:1]
    queryset = Notification.objects.select_related("project", "recipient", "sender").annotate(
        viewer_read_at=Subquery(viewer_receipt, output_field=DateTimeField())
    )
    if project is not None:
        queryset = queryset.filter(project=project)
    if not getattr(user, "is_administrator", False):
        queryset = (
            queryset.exclude(delivery_policy=Notification.DeliveryPolicy.EMAIL_ONLY)
            .filter(
                Q(recipient=user)
                | Q(sender=user)
                | Q(
                    project__memberships__user=user,
                    project__memberships__status="active",
                    project__memberships__role__in=["advisor", "reviewer"],
                )
            )
            .distinct()
        )
    from apps.schedules.models import ScheduleItem

    visible_schedules = ScheduleItem.objects.filter(owner=user) | ScheduleItem.objects.filter(
        scope=ScheduleItem.Scope.GROUP,
        recipient_grants__recipient=user,
        recipient_grants__valid_until__isnull=True,
    )
    if getattr(user, "is_administrator", False):
        visible_schedules |= ScheduleItem.objects.filter(scope=ScheduleItem.Scope.GROUP)
    visible_ids = [
        str(value) for value in visible_schedules.values_list("id", flat=True).distinct()
    ]
    return queryset.filter(
        ~Q(target_type="ScheduleItem") | Q(target_type="ScheduleItem", target_id__in=visible_ids)
    )
