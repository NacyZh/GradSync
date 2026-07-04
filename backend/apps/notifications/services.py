import re

from django.db.models import Q
from django.utils import timezone

from .models import Notification

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
) -> Notification:
    return Notification.objects.create(
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
        eligible_at=eligible_at or timezone.now(),
        failure_reason=mask_notification_failure_reason(failure_reason),
    )


def notification_is_deliverable(notification: Notification) -> bool:
    if notification.project_id is None:
        return True
    return notification.project.memberships.filter(
        user=notification.recipient, status="active"
    ).exists()


def notifications_visible_to(user, *, project=None):
    queryset = Notification.objects.select_related("project", "recipient", "sender")
    if project is not None:
        queryset = queryset.filter(project=project)
    if getattr(user, "is_administrator", False):
        return queryset
    return queryset.filter(
        Q(recipient=user)
        | Q(sender=user)
        | Q(
            project__memberships__user=user,
            project__memberships__status="active",
            project__memberships__role__in=["advisor", "reviewer"],
        )
    ).distinct()
