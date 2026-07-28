import pytest
from rest_framework.test import APIClient

from apps.projects.models import ProjectMembership
from tests.factories.accounts import VerifiedUserFactory
from tests.factories.collaboration import ProjectMembershipFactory, ResearchProjectFactory


@pytest.mark.django_db
def test_unrelated_and_removed_users_cannot_read_execution_ids():
    project = ResearchProjectFactory()
    removed = VerifiedUserFactory()
    unrelated = VerifiedUserFactory()
    ProjectMembershipFactory(
        project=project,
        user=removed,
        role=ProjectMembership.Role.STUDENT,
        status=ProjectMembership.Status.REMOVED,
    )
    client = APIClient()
    for actor in (removed, unrelated):
        client.force_authenticate(actor)
        response = client.get(f"/api/projects/{project.id}/execution-summary/")
        assert response.status_code == 403
        assert project.title not in str(response.data)
