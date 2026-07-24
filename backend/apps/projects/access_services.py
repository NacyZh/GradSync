from apps.accounts.models import User

from .models import ProjectMembership, ResearchProject


def is_active_account(user) -> bool:
    return bool(
        user
        and getattr(user, "is_authenticated", False)
        and user.status == User.Status.ACTIVE
        and user.email_verified_at is not None
    )


def active_membership(user, project: ResearchProject):
    if not is_active_account(user):
        return None
    return project.memberships.filter(
        user=user,
        status=ProjectMembership.Status.ACTIVE,
    ).first()


def is_project_administrator(user) -> bool:
    return bool(is_active_account(user) and user.is_administrator)


def project_capabilities(user, project: ResearchProject) -> dict[str, bool | str]:
    membership = active_membership(user, project)
    role = membership.role if membership else None
    administrator = is_project_administrator(user)
    held = project.governance_state == ResearchProject.GovernanceState.HOLD
    active = project.status == ResearchProject.Status.ACTIVE
    primary = role == ProjectMembership.Role.ADVISOR
    co_advisor = role == ProjectMembership.Role.CO_ADVISOR
    reviewer = role == ProjectMembership.Role.REVIEWER
    student = role == ProjectMembership.Role.STUDENT
    manager = primary or co_advisor
    can_view = bool(membership or administrator)

    return {
        "role": "administrator" if administrator else role or "",
        "canViewProject": can_view,
        "canSuperviseGovernance": administrator,
        "canResolveGovernanceHold": administrator and held,
        "canManageProject": manager and not held,
        "canEditProject": manager and active and not held,
        "canArchiveProject": primary and active and not held,
        "canReopenProject": primary and not active and not held,
        "canDeleteProject": primary and not held,
        "canManageMembers": (manager or administrator) and active and not held,
        "canManageCollaborators": (primary or administrator) and active and not held,
        "canTransferOwnership": (primary or administrator) and not held,
        "canAssignReviews": (manager or administrator) and active and not held,
        "canReviewAssignedTargets": primary or co_advisor or reviewer or administrator,
        "canCreateTasks": manager and active and not held,
        "canUpdateTasks": (manager or student) and active and not held,
        "canMutateProjectWork": manager and active and not held,
        "isReadOnly": bool(can_view and not manager and not student),
        "governanceState": project.governance_state,
        "governanceHoldReason": project.governance_hold_reason,
        "deleteDisabledReason": "governance_hold" if held else "",
    }


def can_access_project(user, project: ResearchProject) -> bool:
    return bool(project_capabilities(user, project)["canViewProject"])

