import pytest

from apps.projects.material_services import project_material_capabilities
from apps.projects.models import ProjectMaterial, ProjectMembership
from apps.projects.permissions import (
    can_access_project_only_material,
    can_change_project_material_visibility,
)
from tests.factories.shared_workspace import (
    active_admin,
    active_student,
    active_teacher,
    project_only_document,
    project_with_members,
)


@pytest.mark.django_db
def test_only_project_advisors_can_change_project_material_visibility():
    owner = active_teacher()
    advisor_member = active_teacher()
    student = active_student()
    admin = active_admin()
    project = project_with_members(advisor=owner, students=[student], reviewers=[advisor_member])

    assert can_change_project_material_visibility(owner, project)
    assert not can_change_project_material_visibility(advisor_member, project)
    assert not can_change_project_material_visibility(admin, project)
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


@pytest.mark.django_db
def test_project_material_download_capability_requires_backing_file():
    student = active_student()
    project = project_with_members(students=[student])
    document = project_only_document(project)
    available = ProjectMaterial.objects.create(
        source_project=project,
        material_type=ProjectMaterial.MaterialType.DOCUMENT,
        backing_record_id=document.id,
        visibility_state=ProjectMaterial.VisibilityState.PROJECT_ONLY,
        classification_state=ProjectMaterial.ClassificationState.ACTIVE,
        classification_reason=ProjectMaterial.ClassificationReason.EXPLICIT_PROJECT_SPECIFIC,
        created_by=project.advisor,
    )
    unavailable = ProjectMaterial.objects.create(
        source_project=project,
        material_type=ProjectMaterial.MaterialType.DOCUMENT,
        backing_record_id=999999,
        visibility_state=ProjectMaterial.VisibilityState.PROJECT_ONLY,
        classification_state=ProjectMaterial.ClassificationState.ACTIVE,
        classification_reason=ProjectMaterial.ClassificationReason.EXPLICIT_PROJECT_SPECIFIC,
        created_by=project.advisor,
    )

    assert project_material_capabilities(student, available)["canDownload"]
    assert not project_material_capabilities(student, unavailable)["canDownload"]
