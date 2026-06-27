import pytest

from apps.projects.models import ProjectMembership, ResearchProject
from apps.submissions.models import Draft
from tests.factories.accounts import UserFactory
from tests.helpers import authenticate


@pytest.mark.django_db
def test_draft_list_handles_project_scoped_records(api_client):
    advisor = UserFactory(global_role="advisor")
    student = UserFactory(global_role="student")
    project = ResearchProject.objects.create(title="Performance", advisor=advisor)
    ProjectMembership.objects.create(project=project, user=student, role="student")
    Draft.objects.bulk_create(
        [Draft(project=project, student=student, title=f"Draft {index}") for index in range(200)]
    )

    response = authenticate(api_client, student).get(f"/api/projects/{project.id}/drafts/")

    assert response.status_code == 200
    assert len(response.json()["results"]) == 50
