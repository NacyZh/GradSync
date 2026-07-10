import pytest

from tests.factories.shared_workspace import (
    active_student,
    group_wide_project_code,
    project_only_document,
    project_with_members,
    standalone_shared_document,
    standalone_shared_paper,
)
from tests.helpers import authenticate


@pytest.mark.django_db
def test_active_users_from_different_projects_discover_same_shared_assets(api_client):
    student_a = active_student()
    student_b = active_student()
    project_a = project_with_members(students=[student_a], title="Project A")
    project_b = project_with_members(students=[student_b], title="Project B")
    paper = standalone_shared_paper(project=project_a, title="Shared Cross Project Paper")
    document = standalone_shared_document(project=project_a, title="Shared Cross Project Document")
    code = group_wide_project_code(project_b, name="Shared Cross Project Code")

    client_a = authenticate(api_client, student_a)
    paper_response = client_a.get("/api/library/papers/?q=Cross")
    document_response = client_a.get("/api/library/documents/?q=Cross")
    code_response = client_a.get("/api/library/code/?q=Cross")

    client_b = authenticate(api_client, student_b)
    second_paper_response = client_b.get("/api/library/papers/?q=Cross")
    second_document_response = client_b.get("/api/library/documents/?q=Cross")
    second_code_response = client_b.get("/api/library/code/?q=Cross")

    assert [item["id"] for item in paper_response.data["results"]] == [paper.id]
    assert [item["id"] for item in document_response.data["results"]] == [document.id]
    assert [item["id"] for item in code_response.data["results"]] == [code.id]
    assert [item["id"] for item in second_paper_response.data["results"]] == [paper.id]
    assert [item["id"] for item in second_document_response.data["results"]] == [document.id]
    assert [item["id"] for item in second_code_response.data["results"]] == [code.id]


@pytest.mark.django_db
def test_project_only_material_is_excluded_from_standalone_shared_sections(api_client):
    student = active_student()
    project = project_with_members(students=[student])
    project_only_document(project, title="Private Project Protocol")

    response = authenticate(api_client, student).get("/api/library/documents/?q=Private")

    assert response.status_code == 200
    assert response.data["results"] == []
