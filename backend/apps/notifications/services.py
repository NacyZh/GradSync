from django.utils import timezone

from .models import Notification


RETRY_NEEDED_STATUSES = {Notification.Status.FAILED}


def notification_needs_retry(notification: Notification) -> bool:
    return notification.status in RETRY_NEEDED_STATUSES


def mark_notification_status(notification: Notification, status: str, failure_reason: str = ""):
    notification.status = status
    if status == Notification.Status.QUEUED:
        notification.queued_at = timezone.now()
    elif status == Notification.Status.SENT:
        notification.sent_at = timezone.now()
    if failure_reason:
        notification.failure_reason = failure_reason
    notification.save(update_fields=["status", "queued_at", "sent_at", "failure_reason"])
    return notification
