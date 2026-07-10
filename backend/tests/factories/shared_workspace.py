from django.utils import timezone

from apps.projects.models import ProjectMembership
from tests.factories.accounts import UserFactory
from tests.factories.collaboration import (
    CodeArtifactFactory,
    CodeArtifactVersionFactory,
    DocumentCategoryFactory,
    DocumentRecordFactory,
    PaperRecordFactory,
    ResearchProjectFactory,
    WritingProjectFactory,
)


def active_student(**overrides):
    overrides.setdefault("global_role", "student")
    overrides.setdefault("status", "active")
    return UserFactory(**overrides)


def active_teacher(**overrides):
    overrides.setdefault("global_role", "advisor")
    overrides.setdefault("status", "active")
    return UserFactory(**overrides)


def active_admin(**overrides):
    overrides.setdefault("global_role", "admin")
    overrides.setdefault("status", "active")
    return UserFactory(**overrides)


def inactive_user(**overrides):
    overrides.setdefault("global_role", "student")
    overrides.setdefault("status", "suspended")
    return UserFactory(**overrides)


def project_with_members(
    *,
    advisor=None,
    students=None,
    reviewers=None,
    title="Shared Boundary Project",
):
    advisor = advisor or active_teacher()
    project = ResearchProjectFactory(title=title, advisor=advisor)
    ProjectMembership.objects.create(
        project=project,
        user=advisor,
        role=ProjectMembership.Role.ADVISOR,
        status=ProjectMembership.Status.ACTIVE,
    )
    for student in students or []:
        ProjectMembership.objects.create(
            project=project,
            user=student,
            role=ProjectMembership.Role.STUDENT,
            status=ProjectMembership.Status.ACTIVE,
        )
    for reviewer in reviewers or []:
        ProjectMembership.objects.create(
            project=project,
            user=reviewer,
            role=ProjectMembership.Role.REVIEWER,
            status=ProjectMembership.Status.ACTIVE,
        )
    return project


def standalone_shared_paper(**overrides):
    overrides.setdefault("boundary_classification", "standalone_shared")
    overrides.setdefault("visibility", "group_wide")
    return PaperRecordFactory(**overrides)


def standalone_shared_document(**overrides):
    overrides.setdefault("boundary_classification", "standalone_shared")
    overrides.setdefault("visibility", "group_wide")
    overrides.setdefault("category", DocumentCategoryFactory())
    return DocumentRecordFactory(**overrides)


def standalone_shared_code(**overrides):
    overrides.setdefault("boundary_classification", "standalone_shared")
    overrides.setdefault("visibility", "group_wide")
    version_overrides = overrides.pop("version", None)
    artifact = CodeArtifactFactory(**overrides)
    if version_overrides is not False:
        CodeArtifactVersionFactory(artifact=artifact, **(version_overrides or {}))
    return artifact


def project_only_document(project, **overrides):
    overrides.setdefault("project", project)
    overrides.setdefault("source_project", project)
    overrides.setdefault("boundary_classification", "project_material")
    overrides.setdefault("visibility", "project_members")
    overrides.setdefault("classification_reason", "explicit_project_specific")
    return DocumentRecordFactory(**overrides)


def group_wide_project_code(project, **overrides):
    overrides.setdefault("project", project)
    overrides.setdefault("source_project", project)
    overrides.setdefault("boundary_classification", "project_material")
    overrides.setdefault("visibility", "group_wide")
    overrides.setdefault("classification_reason", "explicit_project_specific")
    return CodeArtifactFactory(**overrides)


def pending_review_paper(project, **overrides):
    overrides.setdefault("project", project)
    overrides.setdefault("source_project", project)
    overrides.setdefault("boundary_classification", "pending_review")
    overrides.setdefault("classification_reason", "ambiguous_legacy")
    return PaperRecordFactory(**overrides)


def writing_item(*, student=None, project=None, **overrides):
    student = student or active_student()
    project = project or project_with_members(students=[student])
    overrides.setdefault("student", student)
    overrides.setdefault("project", project)
    overrides.setdefault("legacy_project", project)
    overrides.setdefault("migrated_from_project_nested_area", True)
    return WritingProjectFactory(**overrides)


def removed_membership(project, user):
    return ProjectMembership.objects.create(
        project=project,
        user=user,
        role=ProjectMembership.Role.STUDENT,
        status=ProjectMembership.Status.REMOVED,
        removed_at=timezone.now(),
    )
