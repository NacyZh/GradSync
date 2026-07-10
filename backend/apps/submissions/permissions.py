from apps.projects.permissions import is_active_user

from .models import WritingParticipant, WritingProject


def can_access_writing_project(user, writing_project: WritingProject) -> bool:
    if not is_active_user(user):
        return False
    if getattr(user, "is_superuser", False) or getattr(user, "is_administrator", False):
        return True
    if writing_project.student_id == getattr(user, "id", None):
        return True
    return WritingParticipant.objects.filter(
        writing_project=writing_project,
        user=user,
        status=WritingParticipant.Status.ACTIVE,
        participant_role__in=[
            WritingParticipant.Role.BOUND_ADVISOR,
            WritingParticipant.Role.ASSIGNED_REVIEWER,
            WritingParticipant.Role.STUDENT_AUTHOR,
        ],
    ).exists()
