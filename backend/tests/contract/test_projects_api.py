import pytest

from apps.audit.services import record_event
from apps.projects.models import ProjectMaterial, ProjectMembership, ResearchProject
from tests.factories.accounts import UserFactory
from tests.factories.shared_workspace import project_only_document
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
    payload = response.json()
    assert [item["title"] for item in payload["results"]] == ["Visible"]
    assert payload["capabilities"] == {"canCreateProject": True}


@pytest.mark.django_db
def test_student_project_list_exposes_read_only_capabilities(api_client):
    advisor = UserFactory(global_role="advisor")
    student = UserFactory(global_role="student")
    project = ResearchProject.objects.create(title="Student Project", advisor=advisor)
    ProjectMembership.objects.create(project=project, user=student, role="student")

    response = authenticate(api_client, student).get("/api/projects/")

    assert response.status_code == 200
    payload = response.json()
    assert [item["title"] for item in payload["results"]] == ["Student Project"]
    assert payload["capabilities"] == {"canCreateProject": False}


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


@pytest.mark.django_db
def test_project_dashboard_includes_freshness_fields(api_client):
    advisor = UserFactory(global_role="advisor")
    project = ResearchProject.objects.create(title="Scoped", advisor=advisor)
    ProjectMembership.objects.create(project=project, user=advisor, role="advisor")
    event = record_event(project, advisor, "project.updated", "Updated project", project)

    response = authenticate(api_client, advisor).get(f"/api/projects/{project.id}/")

    assert response.status_code == 200
    payload = response.json()
    assert payload["latestEventId"] == f"audit:{event.id}"
    assert payload["freshness"]["state"] == "fresh"
    assert payload["generatedAt"]


@pytest.mark.django_db
def test_project_events_are_scoped_and_bounded(api_client):
    advisor = UserFactory(global_role="advisor")
    project = ResearchProject.objects.create(title="Scoped", advisor=advisor)
    ProjectMembership.objects.create(project=project, user=advisor, role="advisor")
    first = record_event(project, advisor, "project.created", "Created project", project)
    second = record_event(project, advisor, "project.updated", "Updated project", project)

    response = authenticate(api_client, advisor).get(
        f"/api/projects/{project.id}/events/", {"after": f"audit:{first.id}", "limit": "10"}
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["latestEventId"] == f"audit:{second.id}"
    assert payload["generatedAt"]
    assert [item["id"] for item in payload["results"]] == [f"audit:{second.id}"]
    assert payload["results"][0]["eventType"] == "project.updated"


@pytest.mark.django_db
def test_project_events_reject_unauthorized_users(api_client):
    advisor = UserFactory(global_role="advisor")
    outsider = UserFactory(global_role="student")
    project = ResearchProject.objects.create(title="Scoped", advisor=advisor)
    ProjectMembership.objects.create(project=project, user=advisor, role="advisor")

    response = authenticate(api_client, outsider).get(f"/api/projects/{project.id}/events/")

    assert response.status_code == 404


@pytest.mark.django_db
def test_project_material_list_includes_download_capability(api_client):
    advisor = UserFactory(global_role="advisor")
    project = ResearchProject.objects.create(title="Scoped", advisor=advisor)
    ProjectMembership.objects.create(project=project, user=advisor, role="advisor")
    document = project_only_document(project)
    ProjectMaterial.objects.create(
        source_project=project,
        material_type=ProjectMaterial.MaterialType.DOCUMENT,
        backing_record_id=document.id,
        visibility_state=ProjectMaterial.VisibilityState.PROJECT_ONLY,
        classification_state=ProjectMaterial.ClassificationState.ACTIVE,
        classification_reason=ProjectMaterial.ClassificationReason.EXPLICIT_PROJECT_SPECIFIC,
        created_by=advisor,
    )

    response = authenticate(api_client, advisor).get(f"/api/projects/{project.id}/materials/")

    assert response.status_code == 200
    capability = response.json()["results"][0]["actionCapabilities"]
    assert capability["canDownload"] is True


@pytest.mark.django_db
def test_project_material_download_returns_descriptor(api_client):
    advisor = UserFactory(global_role="advisor")
    project = ResearchProject.objects.create(title="Scoped", advisor=advisor)
    ProjectMembership.objects.create(project=project, user=advisor, role="advisor")
    document = project_only_document(project)
    material = ProjectMaterial.objects.create(
        source_project=project,
        material_type=ProjectMaterial.MaterialType.DOCUMENT,
        backing_record_id=document.id,
        visibility_state=ProjectMaterial.VisibilityState.PROJECT_ONLY,
        classification_state=ProjectMaterial.ClassificationState.ACTIVE,
        classification_reason=ProjectMaterial.ClassificationReason.EXPLICIT_PROJECT_SPECIFIC,
        created_by=advisor,
    )

    response = authenticate(api_client, advisor).post(
        f"/api/projects/{project.id}/materials/{material.id}/download/"
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["deliveryMode"] == "direct_response"
    assert payload["filename"]
