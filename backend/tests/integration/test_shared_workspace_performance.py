import time

import pytest

from tests.factories.shared_workspace import active_student, active_teacher, project_with_members
from tests.helpers import authenticate


@pytest.mark.django_db
def test_shared_workspace_project_materials_and_writing_return_within_threshold(api_client):
    advisor = active_teacher()
    student = active_student()
    project = project_with_members(advisor=advisor, students=[student])
    client = authenticate(api_client, student)

    started = time.perf_counter()
    materials_response = client.get(f"/api/projects/{project.id}/materials/")
    writing_response = client.get("/api/writing-projects/")
    elapsed = time.perf_counter() - started

    assert materials_response.status_code == 200
    assert writing_response.status_code == 200
    assert elapsed < 2.0
