import pytest

from apps.accounts.models import StudentProfile
from apps.projects.models import ProjectMembership, ResearchProject
from tests.factories.accounts import UserFactory
from tests.helpers import authenticate


def _student(email: str, nickname: str):
    user = UserFactory(
        email=email,
        name=nickname,
        nickname=nickname,
        global_role="student",
        active_role="student",
        status="active",
    )
    StudentProfile.objects.create(user=user, degree_type=StudentProfile.DegreeType.MASTERS)
    return user


@pytest.mark.django_db
def test_project_member_add_list_remove_contract(api_client):
    teacher = UserFactory(global_role="advisor", status="active")
    student = _student("ada@example.edu", "Ada")
    project = ResearchProject.objects.create(title="Nickname Project", advisor=teacher)
    ProjectMembership.objects.create(project=project, user=teacher, role="advisor")

    add_response = authenticate(api_client, teacher).post(
        f"/api/projects/{project.id}/members/",
        {"studentId": student.id},
        format="json",
    )
    list_response = api_client.get(f"/api/projects/{project.id}/members/")
    remove_response = api_client.delete(
        f"/api/projects/{project.id}/members/{add_response.data['id']}/"
    )

    assert add_response.status_code == 201
    assert add_response.data["projectId"] == project.id
    assert add_response.data["userId"] == student.id
    assert add_response.data["role"] == "student"
    assert add_response.data["status"] == "active"
    assert add_response.data["nickname"] == "Ada"
    assert list_response.status_code == 200
    assert any(member["userId"] == student.id for member in list_response.data)
    assert remove_response.status_code == 204


@pytest.mark.django_db
def test_student_search_disambiguates_duplicate_nicknames_contract(api_client):
    teacher = UserFactory(global_role="advisor", status="active")
    _student("ada.one@example.edu", "Ada")
    _student("ada.two@example.edu", "Ada")

    response = authenticate(api_client, teacher).get("/api/students?q=Ada")

    assert response.status_code == 200
    assert len(response.data) == 2
    assert {item["nickname"] for item in response.data} == {"Ada"}
    assert {item["email"] for item in response.data} == {
        "ada.one@example.edu",
        "ada.two@example.edu",
    }
    assert all("Ada <" in item["label"] for item in response.data)


@pytest.mark.django_db
def test_project_member_contract_rejects_non_student_and_non_advisor(api_client):
    teacher = UserFactory(global_role="advisor", status="active")
    student = _student("student@example.edu", "Student")
    outsider = UserFactory(global_role="student", status="active")
    non_student = UserFactory(global_role="advisor", status="active")
    project = ResearchProject.objects.create(title="Membership Contract", advisor=teacher)
    ProjectMembership.objects.create(project=project, user=teacher, role="advisor")

    non_student_response = authenticate(api_client, teacher).post(
        f"/api/projects/{project.id}/members/",
        {"studentId": non_student.id},
        format="json",
    )
    outsider_response = authenticate(api_client, outsider).post(
        f"/api/projects/{project.id}/members/",
        {"studentId": student.id},
        format="json",
    )

    assert non_student_response.status_code == 400
    assert outsider_response.status_code in {403, 404}
