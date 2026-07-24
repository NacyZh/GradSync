import pytest

from apps.projects.access_services import project_capabilities
from apps.projects.models import ProjectMembership
from tests.factories.accounts import VerifiedUserFactory
from tests.factories.collaboration import ProjectMembershipFactory, ResearchProjectFactory


@pytest.mark.django_db
@pytest.mark.parametrize(
    ("role", "can_manage", "can_review"),
    [
        (ProjectMembership.Role.ADVISOR, True, True),
        (ProjectMembership.Role.CO_ADVISOR, True, True),
        (ProjectMembership.Role.REVIEWER, False, True),
        (ProjectMembership.Role.OBSERVER, False, False),
        (ProjectMembership.Role.STUDENT, False, False),
    ],
)
def test_project_capability_matrix(role, can_manage, can_review):
    project = ResearchProjectFactory()
    user = VerifiedUserFactory(
        global_role="advisor" if role != ProjectMembership.Role.STUDENT else "student",
        active_role="teacher" if role != ProjectMembership.Role.STUDENT else "student",
    )
    ProjectMembershipFactory(project=project, user=user, role=role)

    capabilities = project_capabilities(user, project)

    assert capabilities["canManageProject"] is can_manage
    assert capabilities["canReviewAssignedTargets"] is can_review
    assert capabilities["canViewProject"] is True


@pytest.mark.django_db
def test_administrator_supervises_without_ordinary_project_mutation():
    project = ResearchProjectFactory()
    administrator = VerifiedUserFactory(global_role="admin", active_role="administrator")

    capabilities = project_capabilities(administrator, project)

    assert capabilities["canSuperviseGovernance"] is True
    assert capabilities["canManageProject"] is False
    assert capabilities["canCreateTasks"] is False

