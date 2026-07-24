import pytest
from django.core.exceptions import PermissionDenied

from apps.projects.models import ProjectMembership
from apps.tasks.services import TaskService
from tests.factories.accounts import VerifiedUserFactory
from tests.factories.collaboration import ProjectMembershipFactory, ResearchProjectFactory


@pytest.mark.django_db
@pytest.mark.parametrize("role", ["reviewer", "observer"])
def test_read_only_collaborators_cannot_create_project_tasks(role):
    owner = VerifiedUserFactory(global_role="advisor", active_role="teacher")
    collaborator = VerifiedUserFactory(global_role="advisor", active_role="teacher")
    project = ResearchProjectFactory(advisor=owner)
    ProjectMembershipFactory(project=project, user=owner, role="advisor")
    ProjectMembershipFactory(project=project, user=collaborator, role=role)

    with pytest.raises(PermissionDenied):
        TaskService(collaborator, project).create_task(title="Forbidden")


@pytest.mark.django_db
def test_removed_collaborator_stale_url_returns_not_found(api_client):
    owner = VerifiedUserFactory(global_role="advisor", active_role="teacher")
    collaborator = VerifiedUserFactory(global_role="advisor", active_role="teacher")
    project = ResearchProjectFactory(advisor=owner)
    ProjectMembershipFactory(project=project, user=owner, role="advisor")
    membership = ProjectMembershipFactory(
        project=project,
        user=collaborator,
        role=ProjectMembership.Role.OBSERVER,
        status=ProjectMembership.Status.REMOVED,
    )
    api_client.force_authenticate(collaborator)

    response = api_client.get(f"/api/projects/{project.id}/")
    assert response.status_code == 404
    assert project.title not in str(response.data)
    assert membership.user.email not in str(response.data)

