import pytest

from apps.projects.models import ProjectMembership
from tests.factories.accounts import VerifiedUserFactory
from tests.factories.collaboration import ProjectMembershipFactory, ResearchProjectFactory


@pytest.mark.django_db
def test_owner_searches_and_adds_a_teacher_collaborator(api_client):
    owner = VerifiedUserFactory(global_role="advisor", active_role="teacher")
    project = ResearchProjectFactory(advisor=owner)
    ProjectMembershipFactory(project=project, user=owner, role=ProjectMembership.Role.ADVISOR)
    candidate = VerifiedUserFactory(global_role="advisor", active_role="teacher")
    api_client.force_authenticate(owner)

    search = api_client.get("/api/projects/collaborators/eligible/", {"q": candidate.email[:8]})
    assert search.status_code == 200
    assert [row["id"] for row in search.json()["results"]] == [candidate.id]

    response = api_client.post(
        f"/api/projects/{project.id}/collaborators/",
        {"userId": candidate.id, "role": "co_advisor"},
        format="json",
    )
    assert response.status_code == 201
    assert response.json()["role"] == "co_advisor"


@pytest.mark.django_db
def test_administrator_transfer_requires_reason(api_client):
    owner = VerifiedUserFactory(global_role="advisor", active_role="teacher")
    successor = VerifiedUserFactory(global_role="advisor", active_role="teacher")
    administrator = VerifiedUserFactory(global_role="admin", active_role="administrator")
    project = ResearchProjectFactory(advisor=owner)
    ProjectMembershipFactory(project=project, user=owner, role="advisor")
    api_client.force_authenticate(administrator)

    response = api_client.post(
        f"/api/projects/{project.id}/ownership-transfer/",
        {"newAdvisorId": successor.id, "expectedVersion": 1},
        format="json",
    )
    assert response.status_code == 400

