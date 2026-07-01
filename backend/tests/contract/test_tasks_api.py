import pytest

from apps.projects.models import ProjectMembership, ResearchProject
from apps.tasks.models import Task
from tests.factories.accounts import UserFactory
from tests.helpers import authenticate


@pytest.mark.django_db
def test_member_can_create_project_task(api_client):
    advisor = UserFactory(global_role="advisor")
    student = UserFactory(global_role="student")
    project = ResearchProject.objects.create(title="Project", advisor=advisor)
    ProjectMembership.objects.create(project=project, user=advisor, role="advisor")
    ProjectMembership.objects.create(project=project, user=student, role="student")

    response = authenticate(api_client, advisor).post(
        f"/api/projects/{project.id}/tasks/",
        {"title": "Parent", "assignee_id": student.id, "priority": "high"},
        format="json",
    )

    assert response.status_code == 201
    assert Task.objects.filter(project=project, title="Parent", assignee=student).exists()


@pytest.mark.django_db
def test_task_parent_must_stay_in_project(api_client):
    advisor = UserFactory(global_role="advisor")
    project_a = ResearchProject.objects.create(title="A", advisor=advisor)
    project_b = ResearchProject.objects.create(title="B", advisor=advisor)
    ProjectMembership.objects.create(project=project_a, user=advisor, role="advisor")
    ProjectMembership.objects.create(project=project_b, user=advisor, role="advisor")
    parent = Task.objects.create(project=project_b, title="Other", created_by=advisor)

    response = authenticate(api_client, advisor).post(
        f"/api/projects/{project_a.id}/tasks/",
        {"title": "Invalid", "parent_task_id": parent.id},
        format="json",
    )

    assert response.status_code == 400


@pytest.mark.django_db
def test_member_can_update_child_task_from_project_detail_endpoint(api_client):
    advisor = UserFactory(global_role="advisor")
    student = UserFactory(global_role="student")
    project = ResearchProject.objects.create(title="Project", advisor=advisor)
    ProjectMembership.objects.create(project=project, user=advisor, role="advisor")
    ProjectMembership.objects.create(project=project, user=student, role="student")
    parent = Task.objects.create(
        project=project,
        title="Parent",
        assignee=student,
        created_by=advisor,
    )
    child = Task.objects.create(
        project=project,
        title="Child",
        parent_task=parent,
        assignee=student,
        created_by=advisor,
    )

    response = authenticate(api_client, advisor).patch(
        f"/api/projects/{project.id}/tasks/{child.id}/",
        {"status": "completed"},
        format="json",
    )

    assert response.status_code == 200
    child.refresh_from_db()
    assert child.status == "completed"
