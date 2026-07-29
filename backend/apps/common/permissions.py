from rest_framework.permissions import BasePermission


class IsAdministrator(BasePermission):
    """Only users with global_role='admin' and status='active' may pass."""

    def has_permission(self, request, view) -> bool:
        return bool(
            request.user
            and request.user.is_authenticated
            and request.user.is_administrator
            and request.user.status == request.user.Status.ACTIVE
        )


class IsActiveAccount(BasePermission):
    """Only authenticated accounts in the active lifecycle state may pass."""

    def has_permission(self, request, view) -> bool:
        return bool(
            request.user
            and request.user.is_authenticated
            and request.user.status == request.user.Status.ACTIVE
        )


class IsProjectMember(BasePermission):
    def has_permission(self, request, view) -> bool:
        project_id = (
            view.kwargs.get("project_pk")
            or view.kwargs.get("projectId")
            or view.kwargs.get("project_id")
        )
        if not project_id:
            return bool(request.user and request.user.is_authenticated)
        return user_is_project_member(request.user, project_id)


class IsProjectAdvisor(BasePermission):
    def has_permission(self, request, view) -> bool:
        project_id = (
            view.kwargs.get("project_pk")
            or view.kwargs.get("projectId")
            or view.kwargs.get("project_id")
        )
        if not project_id:
            return bool(request.user and request.user.is_authenticated and request.user.is_advisor)
        return user_has_project_role(request.user, project_id, {"advisor", "reviewer"})


def user_is_project_member(user, project_id) -> bool:
    if not user or not user.is_authenticated:
        return False
    return user.project_memberships.filter(project_id=project_id, status="active").exists()


def user_has_project_role(user, project_id, roles: set[str]) -> bool:
    if not user or not user.is_authenticated:
        return False
    return user.project_memberships.filter(
        project_id=project_id, status="active", role__in=roles
    ).exists()
