import pytest

from apps.projects.models import ProjectMembership, ResearchProject
from tests.factories.accounts import VerifiedUserFactory
from tests.factories.collaboration import ProjectMembershipFactory, ResearchProjectFactory


@pytest.mark.django_db
def test_governance_schema_preserves_student_memberships_and_hold_reason():
    administrator = VerifiedUserFactory(global_role="admin", active_role="administrator")
    student = VerifiedUserFactory(global_role="student", active_role="student")
    project = ResearchProjectFactory(
        advisor=administrator,
        governance_state=ResearchProject.GovernanceState.HOLD,
        governance_hold_reason=ResearchProject.GovernanceHoldReason.LEGACY_ADMIN_OWNER,
    )
    membership = ProjectMembershipFactory(
        project=project,
        user=student,
        role=ProjectMembership.Role.STUDENT,
    )

    membership.refresh_from_db()
    project.refresh_from_db()
    assert membership.status == ProjectMembership.Status.ACTIVE
    assert project.governance_state == ResearchProject.GovernanceState.HOLD
    assert project.governance_hold_reason == "legacy_admin_owner"
