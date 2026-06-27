from django.core.exceptions import PermissionDenied


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
        if not project.memberships.filter(user=self.user, status="active").exists():
            raise PermissionDenied("You are not a member of this project")

    def require_project_reviewer(self, project):
        if not project.memberships.filter(
            user=self.user, status="active", role__in=["advisor", "reviewer"]
        ).exists():
            raise PermissionDenied("You cannot review records in this project")
