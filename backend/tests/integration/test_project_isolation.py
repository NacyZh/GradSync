import pytest

from apps.projects.models import ProjectMembership, ResearchProject
from apps.tasks.models import Task
from tests.factories.accounts import UserFactory
from tests.helpers import authenticate


@pytest.mark.django_db
def test_project_task_lists_do_not_cross_mix(api_client):
    advisor_a = UserFactory(global_role="advisor")
    advisor_b = UserFactory(global_role="advisor")
    project_a = ResearchProject.objects.create(title="A", advisor=advisor_a)
    project_b = ResearchProject.objects.create(title="B", advisor=advisor_b)
    ProjectMembership.objects.create(project=project_a, user=advisor_a, role="advisor")
    ProjectMembership.objects.create(project=project_b, user=advisor_b, role="advisor")
    Task.objects.create(project=project_a, title="A task", created_by=advisor_a)
    Task.objects.create(project=project_b, title="B task", created_by=advisor_b)

    response = authenticate(api_client, advisor_a).get(f"/api/projects/{project_a.id}/tasks/")

    assert response.status_code == 200
    assert [item["title"] for item in response.json()["results"]] == ["A task"]
