from django.contrib.auth import get_user_model
from django.core.exceptions import PermissionDenied
from django.db import transaction
from django.utils import timezone

from apps.audit.services import record_event

from .archive_services import ensure_project_advisor
from .models import ProjectMembership, ResearchProject


class ProjectService:
    def __init__(self, actor):
        self.actor = actor

    @transaction.atomic
    def create_project(
        self,
        *,
        title: str,
        description: str = "",
        starts_on=None,
        ends_on=None,
        student_ids: list[int] | None = None,
    ) -> ResearchProject:
        if not getattr(self.actor, "is_advisor", False):
            raise PermissionDenied("Only advisors can create projects")

        project = ResearchProject.objects.create(
            title=title,
            description=description,
            advisor=self.actor,
            starts_on=starts_on,
            ends_on=ends_on,
        )
        ProjectMembership.objects.create(
            project=project, user=self.actor, role=ProjectMembership.Role.ADVISOR
        )

        users = get_user_model().objects.filter(id__in=student_ids or [])
        for user in users:
            ProjectMembership.objects.get_or_create(
                project=project,
                user=user,
                status=ProjectMembership.Status.ACTIVE,
                defaults={"role": ProjectMembership.Role.STUDENT},
            )
        record_event(
            project, self.actor, "project.created", f"Created project {project.title}", project
        )
        return project

    def update_project(self, project: ResearchProject, **data) -> ResearchProject:
        ensure_project_advisor(self.actor, project)
        for field in ["title", "description", "starts_on", "ends_on"]:
            if field in data:
                setattr(project, field, data[field])
        project.save()
        record_event(
            project, self.actor, "project.updated", f"Updated project {project.title}", project
        )
        return project

    def archive_project(self, project: ResearchProject) -> ResearchProject:
        ensure_project_advisor(self.actor, project)
        project.status = ResearchProject.Status.ARCHIVED
        project.archived_at = timezone.now()
        project.save(update_fields=["status", "archived_at", "updated_at"])
        record_event(
            project, self.actor, "project.archived", f"Archived project {project.title}", project
        )
        return project

    def reopen_project(self, project: ResearchProject) -> ResearchProject:
        ensure_project_advisor(self.actor, project)
        project.status = ResearchProject.Status.ACTIVE
        project.archived_at = None
        project.save(update_fields=["status", "archived_at", "updated_at"])
        record_event(
            project, self.actor, "project.reopened", f"Reopened project {project.title}", project
        )
        return project

    def add_member(self, project: ResearchProject, *, user_id: int, role: str) -> ProjectMembership:
        ensure_project_advisor(self.actor, project)
        membership, _ = ProjectMembership.objects.update_or_create(
            project=project,
            user_id=user_id,
            defaults={"role": role, "status": ProjectMembership.Status.ACTIVE, "removed_at": None},
        )
        record_event(
            project, self.actor, "membership.added", f"Added member {user_id} as {role}", membership
        )
        return membership

    def remove_member(self, membership: ProjectMembership) -> ProjectMembership:
        ensure_project_advisor(self.actor, membership.project)
        membership.status = ProjectMembership.Status.REMOVED
        membership.removed_at = timezone.now()
        membership.save(update_fields=["status", "removed_at"])
        record_event(
            membership.project,
            self.actor,
            "membership.removed",
            f"Removed member {membership.user_id}",
            membership,
        )
        return membership


def projects_visible_to(user):
    if getattr(user, "is_superuser", False):
        return ResearchProject.objects.all()
    return ResearchProject.objects.filter(
        memberships__user=user, memberships__status="active"
    ).distinct()
