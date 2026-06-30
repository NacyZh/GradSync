import pytest

from apps.projects.models import ProjectMembership, ResearchProject
from tests.factories.accounts import UserFactory
from tests.helpers import authenticate


@pytest.mark.django_db
def test_project_list_is_scoped_to_membership(api_client):
    advisor = UserFactory(global_role="advisor")
    other = UserFactory(global_role="advisor")
    visible = ResearchProject.objects.create(title="Visible", advisor=advisor)
    hidden = ResearchProject.objects.create(title="Hidden", advisor=other)
    ProjectMembership.objects.create(project=visible, user=advisor, role="advisor")
    ProjectMembership.objects.create(project=hidden, user=other, role="advisor")

    response = authenticate(api_client, advisor).get("/api/projects/")

    assert response.status_code == 200
    assert [item["title"] for item in response.json()["results"]] == ["Visible"]


@pytest.mark.django_db
def test_advisor_can_create_project_with_students(api_client):
    advisor = UserFactory(global_role="advisor")
    student = UserFactory(global_role="student")

    response = authenticate(api_client, advisor).post(
        "/api/projects/",
        {
            "title": "Project A",
            "description": "Demo",
            "starts_on": "2026-06-25",
            "ends_on": "2026-07-25",
            "student_ids": [student.id],
        },
        format="json",
    )

    assert response.status_code == 201
    project = ResearchProject.objects.get(title="Project A")
    assert str(project.starts_on) == "2026-06-25"
    assert str(project.ends_on) == "2026-07-25"
    assert project.memberships.filter(user=advisor, role="advisor", status="active").exists()
    assert project.memberships.filter(user=student, role="student", status="active").exists()


@pytest.mark.django_db
def test_project_create_rejects_invalid_date_range(api_client):
    advisor = UserFactory(global_role="advisor")

    response = authenticate(api_client, advisor).post(
        "/api/projects/",
        {"title": "Project A", "starts_on": "2026-07-25", "ends_on": "2026-06-25"},
        format="json",
    )

    assert response.status_code == 400
    assert "end date" in response.json()["message"]


@pytest.mark.django_db
def test_project_dashboard_requires_membership(api_client):
    advisor = UserFactory(global_role="advisor")
    outsider = UserFactory(global_role="student")
    project = ResearchProject.objects.create(title="Scoped", advisor=advisor)
    ProjectMembership.objects.create(project=project, user=advisor, role="advisor")

    response = authenticate(api_client, outsider).get(f"/api/projects/{project.id}/")

    assert response.status_code == 404
