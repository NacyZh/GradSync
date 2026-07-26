import pytest

from apps.projects.access_services import project_capabilities
from apps.projects.models import ProjectMembership
from tests.factories.accounts import VerifiedUserFactory
from tests.factories.collaboration import ProjectMembershipFactory, ResearchProjectFactory


@pytest.mark.django_db
@pytest.mark.parametrize(
    ("role", "manage", "recommend", "submit", "policy"),
    [
        ("advisor", True, True, False, True),
        ("co_advisor", True, True, False, False),
        ("reviewer", False, True, False, False),
        ("observer", False, False, False, False),
        ("student", False, False, True, False),
    ],
)
def test_execution_role_capability_matrix(role, manage, recommend, submit, policy):
    project = ResearchProjectFactory()
    user = VerifiedUserFactory(
        global_role="student" if role == "student" else "advisor",
        active_role="student" if role == "student" else "teacher",
    )
    ProjectMembershipFactory(project=project, user=user, role=role)
    capabilities = project_capabilities(user, project)
    assert capabilities["canManageMilestones"] is manage
    assert capabilities["canRecommendDeliverables"] is recommend
    assert capabilities["canSubmitAssignedDeliverables"] is submit
    assert capabilities["canManageProjectNotificationPolicy"] is policy


@pytest.mark.django_db
def test_administrator_only_receives_execution_supervision():
    project = ResearchProjectFactory()
    user = VerifiedUserFactory(global_role="admin", active_role="administrator")
    capabilities = project_capabilities(user, project)
    assert capabilities["canViewExecutionOperations"] is True
    assert capabilities["canManageMilestones"] is False
    assert capabilities["canManageProjectNotificationPolicy"] is False


@pytest.mark.django_db
def test_removed_and_unrelated_users_have_no_execution_access():
    project = ResearchProjectFactory()
    removed = VerifiedUserFactory()
    ProjectMembershipFactory(
        project=project,
        user=removed,
        role=ProjectMembership.Role.STUDENT,
        status=ProjectMembership.Status.REMOVED,
    )
    unrelated = VerifiedUserFactory()
    assert project_capabilities(removed, project)["canViewExecutionSummary"] is False
    assert project_capabilities(unrelated, project)["canViewExecutionSummary"] is False
