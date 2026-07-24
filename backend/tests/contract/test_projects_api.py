import pytest
from django.core.files.base import ContentFile
from django.core.files.storage import default_storage

from apps.audit.services import record_event
from apps.projects.models import ProjectMaterial, ProjectMembership, ResearchProject
from apps.tasks.models import Task
from tests.factories.accounts import UserFactory
from tests.factories.shared_workspace import project_only_document
from tests.helpers import authenticate


def _put_file(storage_key: str, content: bytes = b"project material"):
    if default_storage.exists(storage_key):
        default_storage.delete(storage_key)
    default_storage.save(storage_key, ContentFile(content))


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
def test_project_dashboard_capabilities_are_role_specific(api_client):
    advisor = UserFactory(global_role="advisor")
    student = UserFactory(global_role="student")
    project = ResearchProject.objects.create(title="Role Project", advisor=advisor)
    ProjectMembership.objects.create(project=project, user=advisor, role="advisor")
    ProjectMembership.objects.create(project=project, user=student, role="student")

    advisor_payload = authenticate(api_client, advisor).get(f"/api/projects/{project.id}/").json()
    student_payload = authenticate(api_client, student).get(f"/api/projects/{project.id}/").json()

    assert advisor_payload["capabilities"]["canManageMembers"] is True
    assert advisor_payload["capabilities"]["canCreateTasks"] is True
    assert advisor_payload["capabilities"]["canArchiveProject"] is True
    assert student_payload["capabilities"]["canManageMembers"] is False
    assert student_payload["capabilities"]["canCreateTasks"] is False
    assert student_payload["capabilities"]["canArchiveProject"] is False


@pytest.mark.django_db
def test_admin_can_view_all_projects_without_ordinary_management(api_client):
    admin = UserFactory(global_role="admin")
    advisor = UserFactory(global_role="advisor")
    project = ResearchProject.objects.create(title="Admin Visible", advisor=advisor)
    ProjectMembership.objects.create(project=project, user=advisor, role="advisor")

    list_response = authenticate(api_client, admin).get("/api/projects/")
    detail_response = authenticate(api_client, admin).get(f"/api/projects/{project.id}/")

    assert list_response.status_code == 200
    assert [item["title"] for item in list_response.json()["results"]] == ["Admin Visible"]
    assert detail_response.json()["capabilities"]["canManageProject"] is False
    assert detail_response.json()["capabilities"]["canSuperviseGovernance"] is True


@pytest.mark.django_db
def test_advisor_can_delete_empty_project(api_client):
    advisor = UserFactory(global_role="advisor")
    project = ResearchProject.objects.create(title="Mistaken Project", advisor=advisor)
    ProjectMembership.objects.create(project=project, user=advisor, role="advisor")

    response = authenticate(api_client, advisor).delete(f"/api/projects/{project.id}/")

    assert response.status_code == 204
    assert not ResearchProject.objects.filter(id=project.id).exists()


@pytest.mark.django_db
def test_advisor_can_delete_project_with_research_activity_after_confirmation(api_client):
    advisor = UserFactory(global_role="advisor")
    project = ResearchProject.objects.create(title="Active Project", advisor=advisor)
    ProjectMembership.objects.create(project=project, user=advisor, role="advisor")
    task = Task.objects.create(project=project, title="Real work", created_by=advisor)

    response = authenticate(api_client, advisor).delete(f"/api/projects/{project.id}/")

    assert response.status_code == 204
    assert not ResearchProject.objects.filter(id=project.id).exists()
    assert not Task.objects.filter(id=task.id).exists()


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
def test_project_material_download_returns_file_response(api_client):
    advisor = UserFactory(global_role="advisor")
    project = ResearchProject.objects.create(title="Scoped", advisor=advisor)
    ProjectMembership.objects.create(project=project, user=advisor, role="advisor")
    document = project_only_document(project)
    _put_file(document.document_file.stored_name)
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
    assert response.headers["Content-Disposition"].startswith("attachment;")
