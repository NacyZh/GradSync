import pytest

from apps.projects.models import ProjectMembership, ResearchProject
from apps.tasks.models import Task
from tests.factories.accounts import UserFactory
from tests.helpers import authenticate


@pytest.mark.django_db
def test_project_dashboard_handles_500_active_records(api_client):
    advisor = UserFactory(global_role="advisor")
    project = ResearchProject.objects.create(title="Performance", advisor=advisor)
    ProjectMembership.objects.create(project=project, user=advisor, role="advisor")
    Task.objects.bulk_create(
        [Task(project=project, title=f"Task {index}", created_by=advisor) for index in range(500)]
    )

    response = authenticate(api_client, advisor).get(f"/api/projects/{project.id}/")

    assert response.status_code == 200
    assert response.json()["title"] == "Performance"
