from django.contrib.auth import get_user_model
from django.core.exceptions import PermissionDenied, ValidationError
from django.utils import timezone

from apps.audit.services import record_event
from apps.common.project_scope import ProjectScopedService
from apps.projects.archive_services import ensure_project_writable

from .models import Task

User = get_user_model()


class TaskService(ProjectScopedService):
    def __init__(self, user, project):
        super().__init__(user)
        self.project = project

    def create_task(
        self, *, title: str, parent_task=None, assignee=None, assignee_ids=None, **extra
    ) -> Task:
        self.require_project_member(self.project)
        if not self.project.memberships.filter(
            user=self.user, status="active", role__in=["advisor", "co_advisor"]
        ).exists():
            raise PermissionDenied("Only advisors can create project tasks")
        ensure_project_writable(self.project)
        assignees = self._resolve_assignees(assignee_ids)
        task = Task(
            project=self.project,
            title=title,
            parent_task=parent_task,
            assignee=assignee or (assignees[0] if assignees else None),
            created_by=self.user,
            **extra,
        )
        try:
            task.save()
        except ValidationError:
            raise
        if assignees:
            task.assignees.set(assignees)
        record_event(self.project, self.user, "task.created", f"Created task {task.title}", task)
        return task

    def update_task(self, task: Task, **data) -> Task:
        self.require_project_member(self.project)
        ensure_project_writable(self.project)
        is_advisor = self.project.memberships.filter(
            user=self.user, status="active", role__in=["advisor", "co_advisor"]
        ).exists()
        is_assignee = (
            task.assignee_id == self.user.id
            or task.assignees.filter(id=self.user.id).exists()
        )
        if not (is_advisor or is_assignee):
            raise PermissionDenied("Only advisors or assigned students can update this task")
        advisor_only_fields = {
            "title",
            "description",
            "assignee",
            "assignee_id",
            "assignee_ids",
            "parent_task",
            "parent_task_id",
            "priority",
            "deadline_at",
        }
        if not is_advisor and advisor_only_fields.intersection(data):
            raise PermissionDenied("Only advisors can change task planning fields")
        assignee_ids = data.pop("assignee_ids", None)
        old_status = task.status
        if assignee_ids is not None:
            assignees = self._resolve_assignees(assignee_ids)
            data["assignee"] = assignees[0] if assignees else None
        for field, value in data.items():
            setattr(task, field, value)
        if "status" in data and task.status == Task.Status.COMPLETED:
            task.completed_at = timezone.now()
        task.save()
        if assignee_ids is not None:
            task.assignees.set(assignees)
        if old_status != task.status:
            record_event(
                self.project,
                self.user,
                "task.status_changed",
                f"Changed task {task.title} from {old_status} to {task.status}",
                task,
            )
        else:
            record_event(
                self.project, self.user, "task.updated", f"Updated task {task.title}", task
            )
        return task

    def delete_task(self, task: Task) -> None:
        self.require_project_member(self.project)
        ensure_project_writable(self.project)
        if not self.project.memberships.filter(
            user=self.user, status="active", role__in=["advisor", "co_advisor"]
        ).exists():
            raise PermissionDenied("Only advisors can delete project tasks")
        title = task.title
        record_event(self.project, self.user, "task.deleted", f"Deleted task {title}", task)
        task.delete()

    def _resolve_assignees(self, assignee_ids):
        if assignee_ids is None:
            return []
        normalized_ids = []
        for user_id in assignee_ids:
            if user_id not in normalized_ids:
                normalized_ids.append(user_id)
        if not normalized_ids:
            return []
        active_member_ids = set(
            self.project.memberships.filter(
                user_id__in=normalized_ids, status="active"
            ).values_list("user_id", flat=True)
        )
        invalid_ids = [user_id for user_id in normalized_ids if user_id not in active_member_ids]
        if invalid_ids:
            raise ValidationError("Assignees must be active project members")
        users_by_id = User.objects.in_bulk(normalized_ids)
        return [users_by_id[user_id] for user_id in normalized_ids if user_id in users_by_id]
