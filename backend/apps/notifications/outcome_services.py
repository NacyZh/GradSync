from collections.abc import Callable

from django.core.exceptions import PermissionDenied, ValidationError
from django.db import IntegrityError, transaction
from django.utils import timezone

from apps.audit.services import record_execution_event

from .models import Notification
from .services import enqueue_notification

_ACTION_RESOLVERS: dict[str, Callable[[Notification, str, str], bool]] = {}
TERMINAL_OUTCOMES = {
    Notification.OutcomeState.ACKNOWLEDGED,
    Notification.OutcomeState.COMPLETED,
    Notification.OutcomeState.EXPIRED,
    Notification.OutcomeState.UNAVAILABLE,
}


def register_action_resolver(target_type: str, resolver):
    _ACTION_RESOLVERS[target_type] = resolver


def create_follow_up_notification(*, dedupe_key: str, **kwargs):
    requirement_type = kwargs.get(
        "requirement_type", Notification.RequirementType.ACTION
    )
    kwargs["active_follow_up"] = True
    kwargs["outcome_state"] = Notification.OutcomeState.PENDING
    kwargs["requirement_type"] = requirement_type
    try:
        with transaction.atomic():
            return enqueue_notification(dedupe_key=dedupe_key, **kwargs), True
    except IntegrityError:
        return Notification.objects.get(
            recipient=kwargs["recipient"],
            dedupe_key=dedupe_key,
            active_follow_up=True,
        ), False


@transaction.atomic
def acknowledge_notification(*, notification: Notification, actor):
    locked = Notification.objects.select_for_update().get(pk=notification.pk)
    if locked.recipient_id != actor.pk:
        raise PermissionDenied("Notification acknowledgement is forbidden.")
    if locked.requirement_type != Notification.RequirementType.ACKNOWLEDGEMENT:
        raise ValidationError("This notification does not require acknowledgement.")
    if locked.outcome_state == Notification.OutcomeState.ACKNOWLEDGED:
        return locked
    if locked.outcome_state != Notification.OutcomeState.PENDING:
        raise ValidationError("This notification can no longer be acknowledged.")
    locked.outcome_state = Notification.OutcomeState.ACKNOWLEDGED
    locked.acknowledged_at = timezone.now()
    locked.active_follow_up = False
    locked.save(
        update_fields=["outcome_state", "acknowledged_at", "active_follow_up"]
    )
    record_execution_event(
        project=locked.project,
        actor=actor,
        action="notification.acknowledged",
        target=locked,
        state={"outcomeState": locked.outcome_state},
    )
    return locked


def _transition(notification, outcome, timestamp_field):
    if notification.outcome_state == outcome:
        return notification
    if notification.outcome_state != Notification.OutcomeState.PENDING:
        return notification
    notification.outcome_state = outcome
    setattr(notification, timestamp_field, timezone.now())
    notification.active_follow_up = False
    notification.save(
        update_fields=["outcome_state", timestamp_field, "active_follow_up"]
    )
    return notification


@transaction.atomic
def expire_notification(notification):
    locked = Notification.objects.select_for_update().get(pk=notification.pk)
    return _transition(locked, Notification.OutcomeState.EXPIRED, "expired_at")


@transaction.atomic
def mark_notification_unavailable(notification):
    locked = Notification.objects.select_for_update().get(pk=notification.pk)
    return _transition(locked, Notification.OutcomeState.UNAVAILABLE, "unavailable_at")


@transaction.atomic
def reconcile_authoritative_action(
    *, notification: Notification, event_type: str, event_id: str
):
    locked = Notification.objects.select_for_update().get(pk=notification.pk)
    if locked.requirement_type != Notification.RequirementType.ACTION:
        return locked
    if locked.outcome_state == Notification.OutcomeState.COMPLETED:
        return locked
    resolver = _ACTION_RESOLVERS.get(locked.target_type)
    if resolver is None or not resolver(locked, event_type, str(event_id)):
        return locked
    locked.outcome_state = Notification.OutcomeState.COMPLETED
    locked.action_completed_at = timezone.now()
    locked.completion_event_type = event_type
    locked.completion_event_id = str(event_id)
    locked.active_follow_up = False
    locked.save(
        update_fields=[
            "outcome_state",
            "action_completed_at",
            "completion_event_type",
            "completion_event_id",
            "active_follow_up",
        ]
    )
    return locked


def reconcile_notifications_for_event(
    *,
    project,
    target_type: str,
    target_id: str,
    event_type: str,
    event_id: str,
):
    notifications = Notification.objects.filter(
        project=project,
        target_type=target_type,
        target_id=str(target_id),
        outcome_state=Notification.OutcomeState.PENDING,
        active_follow_up=True,
    )
    for notification in notifications.iterator(chunk_size=100):
        reconcile_authoritative_action(
            notification=notification,
            event_type=event_type,
            event_id=str(event_id),
        )


def register_execution_outcome_resolvers():
    register_action_resolver(
        "DeliverableRevision",
        lambda _notification, event_type, _event_id: event_type
        in {
            "execution.deliverable.recommended",
            "execution.deliverable.decided",
        },
    )
    register_action_resolver(
        "RiskRecord",
        lambda _notification, event_type, _event_id: event_type
        in {"execution.risk.accept", "execution.risk.resolve"},
    )
    register_action_resolver(
        "WeeklyProgressReport",
        lambda _notification, event_type, _event_id: event_type
        in {
            "execution.weekly_report.reviewed",
            "weekly_report.reviewed",
        },
    )
