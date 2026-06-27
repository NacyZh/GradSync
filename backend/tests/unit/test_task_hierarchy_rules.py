import pytest
from django.core.exceptions import ValidationError

from apps.projects.models import ProjectMembership, ResearchProject
from apps.tasks.models import Task
from apps.tasks.services import TaskService
from tests.factories.accounts import UserFactory


@pytest.mark.django_db
def test_task_service_prevents_cross_project_parent():
    advisor = UserFactory(global_role="advisor")
    project_a = ResearchProject.objects.create(title="A", advisor=advisor)
    project_b = ResearchProject.objects.create(title="B", advisor=advisor)
    ProjectMembership.objects.create(project=project_a, user=advisor, role="advisor")
    parent = Task.objects.create(project=project_b, title="Parent", created_by=advisor)

    with pytest.raises(ValidationError):
        TaskService(advisor, project_a).create_task(title="Child", parent_task=parent)


@pytest.mark.django_db
def test_task_clean_prevents_cycle():
    advisor = UserFactory(global_role="advisor")
    project = ResearchProject.objects.create(title="A", advisor=advisor)
    parent = Task.objects.create(project=project, title="Parent", created_by=advisor)
    child = Task.objects.create(
        project=project, title="Child", parent_task=parent, created_by=advisor
    )
    parent.parent_task = child

    with pytest.raises(ValidationError):
        parent.full_clean()
