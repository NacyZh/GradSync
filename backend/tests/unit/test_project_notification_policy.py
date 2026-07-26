import pytest
from django.core.exceptions import PermissionDenied, ValidationError

from apps.notifications.policy_services import effective_project_policy, update_project_policy
from apps.projects.models import ProjectMembership
from tests.factories.accounts import VerifiedUserFactory
from tests.factories.collaboration import ProjectMembershipFactory, ResearchProjectFactory

pytestmark = pytest.mark.django_db


def test_system_defaults_and_primary_advisor_override(settings):
    advisor = VerifiedUserFactory(global_role="advisor", active_role="teacher")
    project = ResearchProjectFactory(advisor=advisor)
    ProjectMembershipFactory(project=project, user=advisor, role="advisor")
    assert effective_project_policy(project)["uses_system_defaults"] is True
    policy = update_project_policy(
        actor=advisor,
        project=project,
        expected_version=0,
        reminder_lead_minutes=120,
        escalation_delay_minutes=180,
        repeat_interval_minutes=240,
        max_reminders=2,
    )
    assert policy.version == 1


@pytest.mark.parametrize("role", ["co_advisor", "student"])
def test_non_primary_member_cannot_update_project_policy(role):
    project = ResearchProjectFactory()
    user = VerifiedUserFactory(
        global_role="student" if role == "student" else "advisor",
        active_role="student" if role == "student" else "teacher",
    )
    ProjectMembershipFactory(project=project, user=user, role=role)
    with pytest.raises(PermissionDenied):
        update_project_policy(actor=user, project=project, expected_version=0)


def test_project_policy_rejects_out_of_range_values():
    advisor = VerifiedUserFactory(global_role="advisor", active_role="teacher")
    project = ResearchProjectFactory(advisor=advisor)
    ProjectMembershipFactory(project=project, user=advisor, role=ProjectMembership.Role.ADVISOR)
    with pytest.raises(ValidationError):
        update_project_policy(
            actor=advisor,
            project=project,
            expected_version=0,
            reminder_lead_minutes=1,
        )
