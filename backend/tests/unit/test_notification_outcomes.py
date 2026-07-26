import pytest

from apps.notifications.models import Notification, NotificationReadReceipt
from apps.notifications.outcome_services import (
    acknowledge_notification,
    expire_notification,
    mark_notification_unavailable,
    reconcile_authoritative_action,
    register_action_resolver,
)
from tests.factories.research_execution import ActionableNotificationFactory

pytestmark = pytest.mark.django_db


def test_read_receipt_does_not_change_pending_outcome():
    notification = ActionableNotificationFactory()
    NotificationReadReceipt.objects.create(
        notification=notification, viewer=notification.recipient
    )
    notification.refresh_from_db()
    assert notification.outcome_state == Notification.OutcomeState.PENDING


def test_acknowledgement_is_terminal_and_idempotent():
    notification = ActionableNotificationFactory(
        requirement_type=Notification.RequirementType.ACKNOWLEDGEMENT
    )
    first = acknowledge_notification(notification=notification, actor=notification.recipient)
    second = acknowledge_notification(notification=first, actor=notification.recipient)
    assert first.acknowledged_at == second.acknowledged_at
    assert second.active_follow_up is False


def test_only_registered_authoritative_resolver_completes_action():
    notification = ActionableNotificationFactory(target_type="TestTarget")
    register_action_resolver(
        "TestTarget", lambda item, event_type, event_id: event_type == "target.completed"
    )
    unchanged = reconcile_authoritative_action(
        notification=notification, event_type="client.completed", event_id="1"
    )
    completed = reconcile_authoritative_action(
        notification=unchanged, event_type="target.completed", event_id="2"
    )
    assert unchanged.outcome_state == Notification.OutcomeState.PENDING
    assert completed.outcome_state == Notification.OutcomeState.COMPLETED
    assert completed.completion_event_id == "2"


def test_expiry_and_unavailable_transitions_are_terminal():
    expired = expire_notification(ActionableNotificationFactory())
    unavailable = mark_notification_unavailable(ActionableNotificationFactory())
    assert expired.outcome_state == Notification.OutcomeState.EXPIRED
    assert unavailable.outcome_state == Notification.OutcomeState.UNAVAILABLE
