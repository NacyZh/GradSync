import pytest

from apps.projects.models import ProjectMembership, ResearchProject
from apps.submissions.models import Draft
from tests.factories.accounts import UserFactory
from tests.helpers import authenticate


@pytest.mark.django_db
def test_student_can_create_draft_and_submit_version(api_client):
    advisor = UserFactory(global_role="advisor")
    student = UserFactory(global_role="student")
    project = ResearchProject.objects.create(title="Project", advisor=advisor)
    ProjectMembership.objects.create(project=project, user=student, role="student")
    draft_response = authenticate(api_client, student).post(
        f"/api/projects/{project.id}/drafts/",
        {"title": "Paper"},
        format="json",
    )
    assert draft_response.status_code == 201

    draft_id = draft_response.json()["id"]
    version_response = api_client.post(
        f"/api/projects/{project.id}/drafts/{draft_id}/versions/",
        {"content_reference": "drafts/paper-v1.docx", "summary": "Initial draft"},
        format="json",
    )
    assert version_response.status_code == 201
    assert version_response.json()["version_number"] == 1


@pytest.mark.django_db
def test_draft_list_is_project_scoped(api_client):
    student = UserFactory(global_role="student")
    other = UserFactory(global_role="student")
    advisor = UserFactory(global_role="advisor")
    project = ResearchProject.objects.create(title="A", advisor=advisor)
    hidden = ResearchProject.objects.create(title="B", advisor=advisor)
    ProjectMembership.objects.create(project=project, user=student, role="student")
    ProjectMembership.objects.create(project=hidden, user=other, role="student")
    Draft.objects.create(project=project, student=student, title="Visible")
    Draft.objects.create(project=hidden, student=other, title="Hidden")

    response = authenticate(api_client, student).get(f"/api/projects/{project.id}/drafts/")

    assert response.status_code == 200
    assert [item["title"] for item in response.json()["results"]] == ["Visible"]
