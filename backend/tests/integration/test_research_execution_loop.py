import pytest

from apps.notifications.models import Notification
from apps.notifications.outcome_services import (
    create_follow_up_notification,
    reconcile_notifications_for_event,
)
from apps.projects.models import ProjectMembership
from tests.factories.accounts import VerifiedUserFactory
from tests.factories.collaboration import ProjectMembershipFactory, ResearchProjectFactory


@pytest.mark.django_db
def test_authoritative_risk_event_completes_linked_action_once():
    advisor = VerifiedUserFactory(global_role="advisor", active_role="teacher")
    project = ResearchProjectFactory(advisor=advisor)
    ProjectMembershipFactory(project=project, user=advisor, role=ProjectMembership.Role.ADVISOR)
    notification, _ = create_follow_up_notification(
        recipient=advisor,
        project=project,
        event_type=Notification.EventType.APPROACHING_DEADLINE,
        target_type="RiskRecord",
        target_id="42",
        subject="Resolve risk",
        action_path=f"/projects/{project.id}/execution?tab=risks",
        category=Notification.Category.RISK,
        requirement_type=Notification.RequirementType.ACTION,
        delivery_policy=Notification.DeliveryPolicy.IN_APP,
        dedupe_key="risk:42:test",
    )
    for _ in range(2):
        reconcile_notifications_for_event(
            project=project,
            target_type="RiskRecord",
            target_id="42",
            event_type="execution.risk.resolve",
            event_id="event-1",
        )
    notification.refresh_from_db()
    assert notification.outcome_state == Notification.OutcomeState.COMPLETED
    assert notification.completion_event_id == "event-1"
