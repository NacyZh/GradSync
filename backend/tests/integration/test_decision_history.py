import pytest
from django.utils import timezone

from apps.projects.decision_risk_services import publish_decision, supersede_decision
from apps.projects.models import ProjectMembership
from tests.factories.accounts import VerifiedUserFactory
from tests.factories.collaboration import ProjectMembershipFactory, ResearchProjectFactory


@pytest.mark.django_db
def test_decision_chain_preserves_predecessor_and_link_snapshot():
    advisor = VerifiedUserFactory(global_role="advisor", active_role="teacher")
    project = ResearchProjectFactory(advisor=advisor)
    ProjectMembershipFactory(project=project, user=advisor, role=ProjectMembership.Role.ADVISOR)
    common = {
        "actor": advisor,
        "project": project,
        "context": "Method selection.",
        "options_considered": ["A", "B"],
        "outcome": "A",
        "rationale": "Validated.",
        "owner_id": advisor.id,
        "effective_date": timezone.localdate(),
    }
    first = publish_decision(**common, title="Initial method", idempotency_key="history-one")
    second = supersede_decision(
        **common,
        predecessor=first,
        title="Updated method",
        idempotency_key="history-two",
    )
    assert second.supersedes_id == first.id
    assert first.superseded_by.id == second.id
