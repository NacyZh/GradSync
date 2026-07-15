import pytest
from django.core.exceptions import PermissionDenied, ValidationError
from django.db import IntegrityError

from apps.projects.models import ProjectMembership, ResearchProject
from apps.projects.services import ProjectService
from tests.factories.accounts import UserFactory


@pytest.mark.django_db
def test_project_service_adds_advisor_membership_on_create():
    advisor = UserFactory(global_role="advisor")

    project = ProjectService(advisor).create_project(title="Thesis", description="", student_ids=[])

    assert project.advisor == advisor
    assert project.memberships.filter(user=advisor, role="advisor", status="active").exists()


@pytest.mark.django_db
def test_project_service_adds_only_selected_active_students_on_create():
    advisor = UserFactory(global_role="advisor")
    student = UserFactory(global_role="student", status="active")

    project = ProjectService(advisor).create_project(
        title="Thesis", description="", student_ids=[student.id]
    )

    assert project.memberships.filter(user=student, role="student", status="active").exists()


@pytest.mark.django_db
def test_project_create_rejects_duplicate_student_selection():
    advisor = UserFactory(global_role="advisor")
    student = UserFactory(global_role="student", status="active")

    with pytest.raises(ValidationError, match="duplicates"):
        ProjectService(advisor).create_project(
            title="Thesis", description="", student_ids=[student.id, student.id]
        )


@pytest.mark.django_db
def test_project_create_rejects_ineligible_student_selection():
    advisor = UserFactory(global_role="advisor")
    teacher = UserFactory(global_role="advisor", status="active")

    with pytest.raises(ValidationError, match="active student"):
        ProjectService(advisor).create_project(
            title="Thesis", description="", student_ids=[teacher.id]
        )


@pytest.mark.django_db
def test_student_cannot_create_project():
    student = UserFactory(global_role="student")

    with pytest.raises(PermissionDenied):
        ProjectService(student).create_project(title="Nope", description="", student_ids=[])


@pytest.mark.django_db
def test_active_membership_is_unique_per_project_user():
    advisor = UserFactory(global_role="advisor")
    project = ResearchProject.objects.create(title="Project", advisor=advisor)
    ProjectMembership.objects.create(project=project, user=advisor, role="advisor")

    with pytest.raises(IntegrityError):
        ProjectMembership.objects.create(project=project, user=advisor, role="advisor")
