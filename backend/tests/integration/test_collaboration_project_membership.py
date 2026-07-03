import pytest

from apps.accounts.models import StudentProfile
from apps.audit.models import AuditEvent
from apps.library.models import DocumentCategory, DocumentRecord, PaperRecord
from apps.projects.models import ProjectMembership, ResearchProject
from tests.factories.accounts import UserFactory
from tests.factories.collaboration import UploadedFileFactory
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
def test_teacher_adds_and_removes_student_by_nickname_selection(api_client):
    teacher = UserFactory(global_role="advisor", status="active")
    student = _student("student@example.edu", "Researcher")
    project = ResearchProject.objects.create(title="Membership", advisor=teacher)
    ProjectMembership.objects.create(project=project, user=teacher, role="advisor")

    search_response = authenticate(api_client, teacher).get("/api/students?q=Researcher")
    add_response = api_client.post(
        f"/api/projects/{project.id}/members/",
        {"studentId": search_response.data[0]["id"]},
        format="json",
    )
    remove_response = api_client.delete(
        f"/api/projects/{project.id}/members/{add_response.data['id']}/"
    )

    membership = ProjectMembership.objects.get(pk=add_response.data["id"])
    assert add_response.status_code == 201
    assert remove_response.status_code == 204
    assert membership.user == student
    membership.refresh_from_db()
    assert membership.status == ProjectMembership.Status.REMOVED
    assert membership.removed_at is not None
    assert AuditEvent.objects.filter(event_type="membership.added", actor=teacher).exists()
    assert AuditEvent.objects.filter(event_type="membership.removed", actor=teacher).exists()


@pytest.mark.django_db
def test_removed_member_loses_project_scoped_access_but_group_wide_remains(api_client):
    teacher = UserFactory(global_role="advisor", status="active")
    student = _student("member@example.edu", "Member")
    project = ResearchProject.objects.create(title="Access", advisor=teacher)
    ProjectMembership.objects.create(project=project, user=teacher, role="advisor")
    membership = ProjectMembership.objects.create(project=project, user=student, role="student")
    PaperRecord.objects.create(
        project=project,
        title="Private Project Paper",
        authors=["A"],
        visibility="project_members",
        created_by=teacher,
    )
    category = DocumentCategory.objects.create(name="General", created_by=teacher)
    DocumentRecord.objects.create(
        project=project,
        category=category,
        title="Group Protocol",
        visibility="group_wide",
        document_file=UploadedFileFactory(owner=teacher),
        checksum_sha256="1" * 64,
        created_by=teacher,
    )
    student_client = authenticate(api_client, student)

    before_private = student_client.get(f"/api/projects/{project.id}/papers/?q=Private")
    before_group = student_client.get(f"/api/projects/{project.id}/documents?q=Group")
    authenticate(api_client, teacher).delete(
        f"/api/projects/{project.id}/members/{membership.id}/"
    )
    authenticate(api_client, student)
    after_private = student_client.get(f"/api/projects/{project.id}/papers/?q=Private")
    after_group = student_client.get(f"/api/projects/{project.id}/documents?q=Group")

    assert len(before_private.data["results"]) == 1
    assert len(before_group.data["results"]) == 1
    assert after_private.status_code == 200
    assert after_private.data["results"] == []
    assert after_group.status_code == 200
    assert len(after_group.data["results"]) == 1


@pytest.mark.django_db
def test_duplicate_nicknames_and_duplicate_active_membership_are_handled(api_client):
    teacher = UserFactory(global_role="advisor", status="active")
    student_one = _student("ada.one@example.edu", "Ada")
    student_two = _student("ada.two@example.edu", "Ada")
    project = ResearchProject.objects.create(title="Duplicates", advisor=teacher)
    ProjectMembership.objects.create(project=project, user=teacher, role="advisor")
    client = authenticate(api_client, teacher)

    search_response = client.get("/api/students?q=Ada")
    first_add = client.post(
        f"/api/projects/{project.id}/members/",
        {"studentId": student_one.id},
        format="json",
    )
    duplicate_add = client.post(
        f"/api/projects/{project.id}/members/",
        {"studentId": student_one.id},
        format="json",
    )
    second_add = client.post(
        f"/api/projects/{project.id}/members/",
        {"studentId": student_two.id},
        format="json",
    )

    assert search_response.status_code == 200
    assert [item["email"] for item in search_response.data] == [
        "ada.one@example.edu",
        "ada.two@example.edu",
    ]
    assert first_add.status_code == 201
    assert duplicate_add.status_code == 400
    assert second_add.status_code == 201
