from datetime import timedelta

import pytest
from django.utils import timezone

from apps.notifications.tasks import create_risk_review_reminders
from apps.projects.decision_risk_services import raise_risk, transition_risk, triage_risk
from apps.projects.models import ProjectMembership
from tests.factories.accounts import VerifiedUserFactory
from tests.factories.collaboration import ProjectMembershipFactory, ResearchProjectFactory


@pytest.mark.django_db
def test_risk_reminder_is_deduplicated_and_stops_after_resolution():
    advisor = VerifiedUserFactory(global_role="advisor", active_role="teacher")
    project = ResearchProjectFactory(advisor=advisor)
    ProjectMembershipFactory(project=project, user=advisor, role=ProjectMembership.Role.ADVISOR)
    risk = raise_risk(
        actor=advisor,
        project=project,
        title="Critical dependency",
        description="External input is late.",
        idempotency_key="lifecycle-risk",
    )
    risk = triage_risk(
        actor=advisor,
        risk=risk,
        expected_version=1,
        likelihood="high",
        impact="high",
        owner_id=advisor.id,
        treatment="Escalate supplier.",
        review_date=timezone.localdate() - timedelta(days=1),
    )
    assert create_risk_review_reminders() == 1
    assert create_risk_review_reminders() == 0
    transition_risk(
        actor=advisor,
        risk=risk,
        expected_version=2,
        action="resolve",
        reason="Input received.",
        idempotency_key="resolve-risk",
    )
    assert create_risk_review_reminders() == 0
