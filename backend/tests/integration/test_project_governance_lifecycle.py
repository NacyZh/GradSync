import pytest
from django.core.exceptions import ValidationError

from apps.projects.collaboration_services import transfer_ownership
from tests.factories.accounts import VerifiedUserFactory
from tests.factories.collaboration import ProjectMembershipFactory, ResearchProjectFactory


@pytest.mark.django_db
def test_transfer_preserves_exactly_one_primary_advisor():
    owner = VerifiedUserFactory(global_role="advisor", active_role="teacher")
    successor = VerifiedUserFactory(global_role="advisor", active_role="teacher")
    project = ResearchProjectFactory(advisor=owner)
    ProjectMembershipFactory(project=project, user=owner, role="advisor")

    transfer_ownership(
        actor=owner,
        project=project,
        new_advisor=successor,
        expected_version=1,
    )

    project.refresh_from_db()
    assert project.advisor == successor
    assert project.memberships.filter(role="advisor", status="active").count() == 1


@pytest.mark.django_db
def test_transfer_rejects_stale_governance_version():
    owner = VerifiedUserFactory(global_role="advisor", active_role="teacher")
    successor = VerifiedUserFactory(global_role="advisor", active_role="teacher")
    project = ResearchProjectFactory(advisor=owner, governance_version=2)
    ProjectMembershipFactory(project=project, user=owner, role="advisor")

    with pytest.raises(ValidationError):
        transfer_ownership(
            actor=owner,
            project=project,
            new_advisor=successor,
            expected_version=1,
        )
