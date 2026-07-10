import pytest

from apps.projects.models import ProjectMembership
from apps.projects.permissions import (
    can_access_project_only_material,
    can_change_project_material_visibility,
)
from tests.factories.shared_workspace import (
    active_admin,
    active_student,
    active_teacher,
    project_with_members,
)


@pytest.mark.django_db
def test_project_owner_advisor_and_admin_can_change_project_material_visibility():
    owner = active_teacher()
    advisor_member = active_teacher()
    student = active_student()
    admin = active_admin()
    project = project_with_members(advisor=owner, students=[student], reviewers=[advisor_member])

    assert can_change_project_material_visibility(owner, project)
    assert can_change_project_material_visibility(advisor_member, project)
    assert can_change_project_material_visibility(admin, project)
    assert not can_change_project_material_visibility(student, project)


@pytest.mark.django_db
def test_project_only_material_access_requires_active_membership_or_admin():
    student = active_student()
    outsider = active_student()
    removed = active_student()
    admin = active_admin()
    project = project_with_members(students=[student])
    ProjectMembership.objects.create(
        project=project,
        user=removed,
        role=ProjectMembership.Role.STUDENT,
        status=ProjectMembership.Status.REMOVED,
    )

    assert can_access_project_only_material(student, project)
    assert can_access_project_only_material(admin, project)
    assert not can_access_project_only_material(outsider, project)
    assert not can_access_project_only_material(removed, project)
