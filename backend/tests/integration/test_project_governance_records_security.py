import pytest
from django.core.exceptions import PermissionDenied

from apps.projects.decision_risk_services import publish_decision, raise_risk
from apps.projects.models import ProjectMembership
from tests.factories.accounts import VerifiedUserFactory
from tests.factories.collaboration import ProjectMembershipFactory, ResearchProjectFactory


@pytest.mark.django_db
def test_unrelated_user_cannot_publish_decision_or_raise_risk():
    advisor = VerifiedUserFactory(global_role="advisor", active_role="teacher")
    unrelated = VerifiedUserFactory(global_role="student", active_role="student")
    project = ResearchProjectFactory(advisor=advisor)
    ProjectMembershipFactory(project=project, user=advisor, role=ProjectMembership.Role.ADVISOR)
    with pytest.raises(PermissionDenied):
        raise_risk(
            actor=unrelated,
            project=project,
            title="Hidden",
            description="Must not be created.",
        )
    with pytest.raises(PermissionDenied):
        publish_decision(
            actor=unrelated,
            project=project,
            title="Hidden",
            context="Hidden",
            options_considered=["A"],
            outcome="A",
            rationale="Hidden",
            owner_id=advisor.id,
            effective_date=project.starts_on,
        )
