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
def test_student_search_marks_existing_project_member_eligibility(api_client):
    teacher = UserFactory(global_role="advisor", status="active")
    existing = _student("existing@example.edu", "Ada")
    _student("available@example.edu", "Ada")
    project = ResearchProject.objects.create(title="Eligibility Project", advisor=teacher)
    ProjectMembership.objects.create(project=project, user=teacher, role="advisor")
    ProjectMembership.objects.create(project=project, user=existing, role="student")

    response = authenticate(api_client, teacher).get(
        f"/api/accounts/students/?q=Ada&projectId={project.id}"
    )

    assert response.status_code == 200
    by_email = {item["email"]: item for item in response.data}
    assert by_email["existing@example.edu"]["eligibility"] == {
        "selectable": False,
        "reason": "already_active_member",
    }
    assert by_email["available@example.edu"]["eligibility"] == {
        "selectable": True,
        "reason": "",
    }


@pytest.mark.django_db
def test_project_create_contract_accepts_student_ids_camel_case(api_client):
    teacher = UserFactory(global_role="advisor", status="active")
    student = _student("selected@example.edu", "Selected")

    response = authenticate(api_client, teacher).post(
        "/api/projects/",
        {"title": "Created With Student", "studentIds": [student.id]},
        format="json",
    )

    assert response.status_code == 201
    project = ResearchProject.objects.get(title="Created With Student")
    assert project.memberships.filter(user=student, role="student", status="active").exists()


@pytest.mark.django_db
def test_project_create_contract_rejects_ineligible_student_ids(api_client):
    teacher = UserFactory(global_role="advisor", status="active")
    non_student = UserFactory(global_role="advisor", status="active")

    response = authenticate(api_client, teacher).post(
        "/api/projects/",
        {"title": "Invalid Student", "studentIds": [non_student.id]},
        format="json",
    )

    assert response.status_code == 400
    assert "active student" in response.data["message"]


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
