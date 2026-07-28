from datetime import timedelta

import pytest
from django.utils import timezone

from apps.projects.decision_risk_services import publish_decision, supersede_decision
from apps.projects.models import DecisionRecord, ProjectMembership
from tests.factories.accounts import VerifiedUserFactory
from tests.factories.collaboration import ProjectMembershipFactory, ResearchProjectFactory


@pytest.mark.django_db
def test_decision_is_idempotent_immutable_and_has_one_successor():
    advisor = VerifiedUserFactory(global_role="advisor", active_role="teacher")
    project = ResearchProjectFactory(advisor=advisor)
    ProjectMembershipFactory(project=project, user=advisor, role=ProjectMembership.Role.ADVISOR)
    payload = {
        "actor": advisor,
        "project": project,
        "title": "Select method",
        "context": "A reproducible method is required.",
        "options_considered": ["Method A", "Method B"],
        "outcome": "Use method A.",
        "rationale": "It has stronger validation.",
        "owner_id": advisor.id,
        "effective_date": timezone.localdate(),
        "idempotency_key": "decision-key-001",
    }
    first = publish_decision(**payload)
    assert publish_decision(**payload).id == first.id
    successor = supersede_decision(
        **{
            **payload,
            "predecessor": first,
            "title": "Refine method",
            "effective_date": timezone.localdate() + timedelta(days=1),
            "idempotency_key": "decision-key-002",
        }
    )
    first.refresh_from_db()
    assert first.status == DecisionRecord.Status.SUPERSEDED
    assert successor.supersedes_id == first.id
    with pytest.raises(ValueError, match="current"):
        supersede_decision(
            **{
                **payload,
                "predecessor": first,
                "idempotency_key": "decision-key-003",
            }
        )
    with pytest.raises(ValueError, match="deleted"):
        successor.delete()
