from __future__ import annotations

from django.core.exceptions import PermissionDenied
from django.db.models import Q

from apps.projects.models import ProjectMembership, ResearchProject
from apps.projects.permissions import is_active_user

from .models import WritingParticipant, WritingProject


def _is_admin(user) -> bool:
    return bool(getattr(user, "is_superuser", False) or getattr(user, "is_administrator", False))


def _active_participants(writing_project: WritingProject):
    return WritingParticipant.objects.filter(
        writing_project=writing_project,
        status=WritingParticipant.Status.ACTIVE,
    )


def participant_role_for(user, writing_project: WritingProject) -> str:
    if not is_active_user(user):
        return ""
    if _is_admin(user):
        return WritingParticipant.Role.ADMINISTRATOR
    participant = (
        _active_participants(writing_project)
        .filter(user=user)
        .order_by("id")
        .first()
    )
    if participant:
        return participant.participant_role
    if writing_project.student_id == getattr(user, "id", None):
        return WritingParticipant.Role.STUDENT_AUTHOR
    return ""


def can_review_writing_project(user, writing_project: WritingProject) -> bool:
    role = participant_role_for(user, writing_project)
    if role in {
        WritingParticipant.Role.BOUND_ADVISOR,
        WritingParticipant.Role.ASSIGNED_REVIEWER,
        WritingParticipant.Role.ADMINISTRATOR,
    }:
        return True

    project = writing_project.project
    return bool(
        project
        and project.memberships.filter(
            user=user,
            status=ProjectMembership.Status.ACTIVE,
            role__in=[ProjectMembership.Role.ADVISOR, ProjectMembership.Role.REVIEWER],
        ).exists()
    )


def ensure_default_writing_participants(writing_project: WritingProject) -> None:
    WritingParticipant.objects.get_or_create(
        writing_project=writing_project,
        user=writing_project.student,
        status=WritingParticipant.Status.ACTIVE,
        defaults={"participant_role": WritingParticipant.Role.STUDENT_AUTHOR},
    )

    project = writing_project.legacy_project or writing_project.project
    if project and project.advisor_id:
        WritingParticipant.objects.get_or_create(
            writing_project=writing_project,
            user=project.advisor,
            status=WritingParticipant.Status.ACTIVE,
            defaults={"participant_role": WritingParticipant.Role.BOUND_ADVISOR},
        )


def writing_projects_for_user(user):
    queryset = (
        WritingProject.objects.select_related("student", "project", "legacy_project")
        .prefetch_related(
            "participants",
            "versions__draft_file",
            "versions__feedback__annotated_file",
            "versions__feedback__notification",
        )
        .distinct()
    )
    if not is_active_user(user):
        return queryset.none()
    if _is_admin(user):
        return queryset
    return queryset.filter(
        Q(student=user)
        | Q(participants__user=user, participants__status=WritingParticipant.Status.ACTIVE)
    ).distinct()


def require_writing_access(user, writing_project: WritingProject) -> None:
    if not participant_role_for(user, writing_project):
        raise PermissionDenied("You are not authorized to access this writing item")


def require_student_author(user, writing_project: WritingProject) -> None:
    if participant_role_for(user, writing_project) != WritingParticipant.Role.STUDENT_AUTHOR:
        raise PermissionDenied("Only the student author can upload writing versions")


def anchor_project_for_standalone_writing(user) -> ResearchProject:
    if not is_active_user(user):
        raise PermissionDenied("Only active users can create writing projects")
    membership = (
        ProjectMembership.objects.select_related("project")
        .filter(
            user=user,
            status=ProjectMembership.Status.ACTIVE,
            role=ProjectMembership.Role.STUDENT,
            project__status=ResearchProject.Status.ACTIVE,
        )
        .order_by("project__title", "project_id")
        .first()
    )
    if not membership:
        raise PermissionDenied("Writing projects require an active student project")
    return membership.project
