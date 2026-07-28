from datetime import timedelta

import pytest
from django.utils import timezone

from apps.projects.decision_risk_services import raise_risk, transition_risk, triage_risk
from apps.projects.models import ProjectMembership, RiskRecord
from tests.factories.accounts import VerifiedUserFactory
from tests.factories.collaboration import ProjectMembershipFactory, ResearchProjectFactory


@pytest.mark.django_db
def test_risk_triage_close_and_reopen_preserves_revision_history():
    advisor = VerifiedUserFactory(global_role="advisor", active_role="teacher")
    project = ResearchProjectFactory(advisor=advisor)
    ProjectMembershipFactory(project=project, user=advisor, role=ProjectMembership.Role.ADVISOR)
    risk = raise_risk(
        actor=advisor,
        project=project,
        title="Dataset delay",
        description="Collection is behind plan.",
        idempotency_key="risk-raise-001",
    )
    risk = triage_risk(
        actor=advisor,
        risk=risk,
        expected_version=1,
        likelihood="high",
        impact="medium",
        owner_id=advisor.id,
        treatment="Add a second collection window.",
        review_date=timezone.localdate() + timedelta(days=2),
    )
    assert risk.severity == "high"
    risk = transition_risk(
        actor=advisor,
        risk=risk,
        expected_version=2,
        action="resolve",
        reason="Collection completed.",
        idempotency_key="risk-close-001",
    )
    assert risk.state == RiskRecord.State.RESOLVED
    assert risk.closed_at is not None
    risk = transition_risk(
        actor=advisor,
        risk=risk,
        expected_version=3,
        action="reopen",
        reason="Validation found missing samples.",
        owner_id=advisor.id,
        review_date=timezone.localdate() + timedelta(days=3),
        idempotency_key="risk-reopen-001",
    )
    assert risk.state == RiskRecord.State.OPEN
    assert risk.closed_at is None
    assert risk.revisions.count() == 4
