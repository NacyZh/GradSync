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

        for user in _eligible_project_students(student_ids or []):
            membership = ProjectMembership.objects.create(
                project=project,
                user=user,
                status=ProjectMembership.Status.ACTIVE,
                role=ProjectMembership.Role.STUDENT,
            )
            record_membership_change(project, self.actor, membership, "added")
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

    def delete_project(self, project: ResearchProject) -> None:
        ensure_project_advisor(self.actor, project)
        blockers = project_delete_blockers(project)
        if blockers:
            raise ValidationError(
                "Projects with research activity cannot be deleted; archive the project instead"
            )
        project.delete()

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
    if getattr(user, "is_superuser", False) or getattr(user, "is_administrator", False):
        return ResearchProject.objects.all()
    return ResearchProject.objects.filter(
        memberships__user=user, memberships__status="active"
    ).distinct()


def can_create_projects(user) -> bool:
    return bool(getattr(user, "is_authenticated", False) and getattr(user, "is_advisor", False))


def can_manage_project(user, project: ResearchProject) -> bool:
    if not getattr(user, "is_authenticated", False):
        return False
    if getattr(user, "is_administrator", False):
        return True
    return project.memberships.filter(
        user=user,
        status=ProjectMembership.Status.ACTIVE,
        role=ProjectMembership.Role.ADVISOR,
    ).exists()


def project_delete_blockers(project: ResearchProject) -> list[str]:
    checks = {
        "tasks": project.tasks,
        "materials": project.materials,
        "drafts": project.drafts,
        "draft versions": project.draft_versions,
        "weekly reports": project.weekly_reports,
        "comments": project.inline_comments,
        "writing projects": project.writing_projects,
        "bookings": project.bookings,
        "paper records": project.paper_records,
        "document records": project.document_records,
        "code artifacts": project.code_artifacts,
    }
    return [label for label, manager in checks.items() if manager.exists()]


def project_capabilities(user, project: ResearchProject) -> dict:
    can_manage = can_manage_project(user, project)
    writable = project.status == ResearchProject.Status.ACTIVE
    delete_blockers = project_delete_blockers(project)
    return {
        "canManageProject": can_manage,
        "canEditProject": can_manage,
        "canArchiveProject": can_manage and writable,
        "canReopenProject": can_manage and project.status == ResearchProject.Status.ARCHIVED,
        "canDeleteProject": can_manage and not delete_blockers,
        "canManageMembers": can_manage and writable,
        "canCreateTasks": can_manage and writable,
        "canUpdateTasks": can_manage and writable,
        "deleteDisabledReason": (
            "Projects with research activity must be archived instead of deleted"
            if can_manage and delete_blockers
            else ""
        ),
    }


def _eligible_project_students(student_ids: list[int]):
    if not student_ids:
        return []
    if len(student_ids) != len(set(student_ids)):
        raise ValidationError("Student selections must not contain duplicates")

    user_model = get_user_model()
    students = list(user_model.objects.filter(id__in=student_ids))
    found_ids = {student.id for student in students}
    if found_ids != set(student_ids):
        raise ValidationError("Selected student does not exist")

    for student in students:
        if (
            student.global_role != student.GlobalRole.STUDENT
            or student.status != student.Status.ACTIVE
            or student.active_role != student.RequestedRole.STUDENT
        ):
            raise ValidationError("Selected account is not an active student")
    return students


def project_event_feed(project: ResearchProject, *, after: str | None = None, limit: int = 50):
    after_source = None
    after_id = None
    if after and ":" in after:
        after_source, raw_id = after.split(":", 1)
        if raw_id.isdigit():
            after_id = int(raw_id)

    events = []
    audit_events = project.audit_events.select_related("actor").order_by("-created_at")[:limit]
    for event in audit_events:
        event_id = f"audit:{event.id}"
        if after_source == "audit" and after_id is not None and event.id <= after_id:
            continue
        events.append(
            {
                "id": event_id,
                "source": "audit",
                "eventType": event.event_type,
                "targetType": event.target_type,
                "targetId": event.target_id,
                "summary": event.summary,
                "actorId": event.actor_id,
                "createdAt": event.created_at,
            }
        )

    download_events = project.download_events.select_related("actor").order_by("-downloaded_at")[
        :limit
    ]
    for event in download_events:
        event_id = f"download:{event.id}"
        if after_source == "download" and after_id is not None and event.id <= after_id:
            continue
        events.append(
            {
                "id": event_id,
                "source": "download",
                "eventType": f"download.{event.target_type}",
                "targetType": event.target_type,
                "targetId": event.target_id,
                "summary": f"Downloaded {event.filename}",
                "actorId": event.actor_id,
                "createdAt": event.downloaded_at,
            }
        )

    notification_events = project.notifications.select_related("sender").order_by("-created_at")[
        :limit
    ]
    for notification in notification_events:
        event_id = f"notification:{notification.id}"
        if after_source == "notification" and after_id is not None and notification.id <= after_id:
            continue
        events.append(
            {
                "id": event_id,
                "source": "notification",
                "eventType": f"notification.{notification.status}",
                "targetType": notification.target_type,
                "targetId": notification.target_id,
                "summary": notification.subject,
                "actorId": notification.sender_id,
                "createdAt": notification.created_at,
            }
        )

    comment_events = project.inline_comments.select_related("author").order_by("-created_at")[
        :limit
    ]
    for comment in comment_events:
        event_id = f"comment:{comment.id}"
        if after_source == "comment" and after_id is not None and comment.id <= after_id:
            continue
        events.append(
            {
                "id": event_id,
                "source": "comment",
                "eventType": f"inline_comment.{comment.status}",
                "targetType": comment.target_type,
                "targetId": str(comment.target_id),
                "summary": (
                    f"Comment on {comment.target_type} {comment.target_id}: {comment.anchor}"
                ),
                "actorId": comment.author_id,
                "createdAt": comment.created_at,
            }
        )

    events = sorted(events, key=lambda item: item["createdAt"], reverse=True)
    return events[: max(1, min(limit, 100))]
