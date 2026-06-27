from django.core.exceptions import PermissionDenied


def ensure_project_writable(project):
    if project.status == "archived":
        raise PermissionDenied("Archived projects are read-only until reopened")


def ensure_project_advisor(user, project):
    if not project.memberships.filter(user=user, status="active", role="advisor").exists():
        raise PermissionDenied("Only project advisors can perform this action")
