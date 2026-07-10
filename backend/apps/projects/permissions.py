from apps.accounts.models import User

from .models import ProjectMembership, ResearchProject


def is_active_user(user) -> bool:
    return bool(
        user
        and getattr(user, "is_authenticated", False)
        and getattr(user, "status", None) == User.Status.ACTIVE
    )


def is_project_owner_or_advisor(user, project: ResearchProject) -> bool:
    if not is_active_user(user):
        return False
    if project.advisor_id == getattr(user, "id", None):
        return True
    return project.memberships.filter(
        user=user,
        status=ProjectMembership.Status.ACTIVE,
        role__in=[ProjectMembership.Role.ADVISOR, ProjectMembership.Role.REVIEWER],
    ).exists()


def is_admin_user(user) -> bool:
    return bool(
        is_active_user(user)
        and (getattr(user, "is_superuser", False) or getattr(user, "is_administrator", False))
    )


def can_change_project_material_visibility(user, project: ResearchProject) -> bool:
    return is_admin_user(user) or is_project_owner_or_advisor(user, project)


def can_access_project_only_material(user, project: ResearchProject) -> bool:
    if is_admin_user(user):
        return True
    if not is_active_user(user):
        return False
    return project.memberships.filter(
        user=user,
        status=ProjectMembership.Status.ACTIVE,
    ).exists()
