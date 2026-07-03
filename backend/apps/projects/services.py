from django.contrib.auth import get_user_model
from django.core.exceptions import PermissionDenied, ValidationError
from django.db import transaction
from django.utils import timezone

from apps.audit.services import record_event, record_membership_change
from apps.notifications.models import Notification

from .archive_services import ensure_project_advisor, ensure_project_writable
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
        ensure_project_writable(project)
        membership, _ = ProjectMembership.objects.update_or_create(
            project=project,
            user_id=user_id,
            defaults={"role": role, "status": ProjectMembership.Status.ACTIVE, "removed_at": None},
        )
        record_membership_change(project, self.actor, membership, "added")
        self._notify_membership_change(membership, "Project membership added")
        return membership

    @transaction.atomic
    def add_student_member(self, project: ResearchProject, *, student_id: int) -> ProjectMembership:
        ensure_project_advisor(self.actor, project)
        ensure_project_writable(project)
        user_model = get_user_model()
        try:
            student = user_model.objects.get(pk=student_id)
        except user_model.DoesNotExist as exc:
            raise ValidationError("Selected student does not exist") from exc
        if (
            student.global_role != student.GlobalRole.STUDENT
            or student.status != student.Status.ACTIVE
            or student.active_role != student.RequestedRole.STUDENT
        ):
            raise ValidationError("Selected account is not an active student")
        existing = ProjectMembership.objects.filter(project=project, user=student).first()
        if existing and existing.status == ProjectMembership.Status.ACTIVE:
            raise ValidationError("Student is already an active project member")
        if existing:
            existing.role = ProjectMembership.Role.STUDENT
            existing.status = ProjectMembership.Status.ACTIVE
            existing.removed_at = None
            existing.save(update_fields=["role", "status", "removed_at"])
            membership = existing
        else:
            membership = ProjectMembership.objects.create(
                project=project,
                user=student,
                role=ProjectMembership.Role.STUDENT,
            )
        record_membership_change(project, self.actor, membership, "added")
        self._notify_membership_change(membership, "Project membership added")
        return membership

    def remove_member(self, membership: ProjectMembership) -> ProjectMembership:
        ensure_project_advisor(self.actor, membership.project)
        ensure_project_writable(membership.project)
        if (
            membership.role == ProjectMembership.Role.ADVISOR
            and membership.user_id == self.actor.id
        ):
            raise ValidationError("Project advisors cannot remove their own membership")
        if membership.status == ProjectMembership.Status.REMOVED:
            return membership
        membership.status = ProjectMembership.Status.REMOVED
        membership.removed_at = timezone.now()
        membership.save(update_fields=["status", "removed_at"])
        record_membership_change(membership.project, self.actor, membership, "removed")
        self._notify_membership_change(membership, "Project membership removed")
        return membership

    def _notify_membership_change(self, membership: ProjectMembership, subject: str) -> None:
        Notification.objects.create(
            project=membership.project,
            recipient=membership.user,
            sender=self.actor,
            event_type=Notification.EventType.MEMBERSHIP_CHANGED,
            target_type="ProjectMembership",
            target_id=str(membership.id),
            subject=subject,
            action_path=f"/projects/{membership.project_id}",
            eligible_at=timezone.now(),
        )


def projects_visible_to(user):
    if getattr(user, "is_superuser", False):
        return ResearchProject.objects.all()
    return ResearchProject.objects.filter(
        memberships__user=user, memberships__status="active"
    ).distinct()
