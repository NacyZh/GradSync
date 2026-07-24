from apps.accounts.models import User

from .access_services import project_capabilities
from .models import ProjectMembership, ResearchProject


def is_active_user(user) -> bool:
    return bool(
        user
        and getattr(user, "is_authenticated", False)
        and getattr(user, "status", None) == User.Status.ACTIVE
    )


def is_project_owner_or_advisor(user, project: ResearchProject) -> bool:
    return bool(project_capabilities(user, project)["canMutateProjectWork"])


def is_admin_user(user) -> bool:
    return bool(
        is_active_user(user)
        and (getattr(user, "is_superuser", False) or getattr(user, "is_administrator", False))
    )


def can_change_project_material_visibility(user, project: ResearchProject) -> bool:
    return is_project_owner_or_advisor(user, project)


def can_access_project_only_material(user, project: ResearchProject) -> bool:
    if is_admin_user(user):
        return True
    if not is_active_user(user):
        return False
    return project.memberships.filter(
        user=user,
        status=ProjectMembership.Status.ACTIVE,
    ).exists()
