from django.core.exceptions import PermissionDenied
from django.db.models import Q

PROJECT_MEMBERS = "project_members"
GROUP_WIDE = "group_wide"


def user_is_active_project_member(user, project) -> bool:
    return bool(
        user
        and user.is_authenticated
        and project.memberships.filter(user=user, status="active").exists()
    )


def can_access_asset(user, *, project, visibility: str) -> bool:
    if not user or not user.is_authenticated:
        return False
    if getattr(user, "is_superuser", False) or getattr(user, "is_administrator", False):
        return True
    if visibility == GROUP_WIDE:
        return True
    return user_is_active_project_member(user, project)


def visible_asset_q(user, project_field: str = "project", visibility_field: str = "visibility"):
    if not user or not user.is_authenticated:
        return Q(pk__in=[])
    if getattr(user, "is_superuser", False) or getattr(user, "is_administrator", False):
        return Q()
    return Q(**{visibility_field: GROUP_WIDE}) | Q(
        **{
            f"{project_field}__memberships__user": user,
            f"{project_field}__memberships__status": "active",
        }
    )


def filter_visible_assets(assets, user):
    return [
        asset
        for asset in assets
        if can_access_asset(user, project=asset.project, visibility=asset.visibility)
    ]


class ProjectScopedQuerySetMixin:
    project_lookup = "project_id"

    def scope_to_user(self, queryset, user):
        if not user or not user.is_authenticated:
            return queryset.none()
        if getattr(user, "is_superuser", False):
            return queryset
        return queryset.filter(
            project__memberships__user=user, project__memberships__status="active"
        ).distinct()


class ProjectScopedService:
    def __init__(self, user):
        self.user = user

    def require_project_member(self, project):
        if not user_is_active_project_member(self.user, project):
            raise PermissionDenied("You are not a member of this project")

    def require_project_reviewer(self, project):
        if getattr(self.user, "is_administrator", False):
            return
        if not project.memberships.filter(
            user=self.user, status="active", role__in=["advisor", "co_advisor", "reviewer"]
        ).exists():
            raise PermissionDenied("You cannot review records in this project")
