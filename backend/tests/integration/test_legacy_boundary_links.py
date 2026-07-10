import pytest

from tests.factories.shared_workspace import active_student, active_teacher, project_with_members
from tests.helpers import authenticate


@pytest.mark.django_db
def test_legacy_project_link_resolves_to_standalone_section_for_member(api_client):
    advisor = active_teacher()
    student = active_student()
    project = project_with_members(advisor=advisor, students=[student])

    response = authenticate(api_client, student).post(
        "/api/boundary/legacy-link/",
        {"path": f"/projects/{project.id}/documents"},
        format="json",
    )

    assert response.status_code == 200
    assert response.data == {
        "mode": "redirect",
        "targetPath": "/library/documents",
        "message": "This workspace section moved out of project navigation.",
    }


@pytest.mark.django_db
def test_legacy_project_link_denial_does_not_leak_metadata(api_client):
    advisor = active_teacher()
    outsider = active_student()
    project = project_with_members(advisor=advisor, title="Private Boundary Project")

    response = authenticate(api_client, outsider).post(
        "/api/boundary/legacy-link/",
        {"path": f"/projects/{project.id}/documents"},
        format="json",
    )

    assert response.status_code == 403
    assert response.data["mode"] == "denied"
    assert "Private Boundary Project" not in str(response.data)


@pytest.mark.django_db
def test_legacy_writing_link_returns_standalone_guidance_without_titles(api_client):
    advisor = active_teacher()
    student = active_student()
    project = project_with_members(advisor=advisor, students=[student])

    response = authenticate(api_client, advisor).post(
        "/api/boundary/legacy-link/",
        {"path": f"/projects/{project.id}/writing"},
        format="json",
    )

    assert response.status_code == 200
    assert response.data["mode"] == "guidance"
    assert response.data["targetPath"] == "/writing"
