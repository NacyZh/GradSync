from django.core.exceptions import PermissionDenied, ValidationError
from django.utils import timezone

from apps.audit.services import record_event
from apps.common.project_scope import ProjectScopedService
from apps.projects.archive_services import ensure_project_writable

from .models import Task


class TaskService(ProjectScopedService):
    def __init__(self, user, project):
        super().__init__(user)
        self.project = project

    def create_task(self, *, title: str, parent_task=None, assignee=None, **extra) -> Task:
        self.require_project_member(self.project)
        if not self.project.memberships.filter(
            user=self.user, status="active", role__in=["advisor", "reviewer"]
        ).exists():
            raise PermissionDenied("Only advisors can create project tasks")
        ensure_project_writable(self.project)
        task = Task(
            project=self.project,
            title=title,
            parent_task=parent_task,
            assignee=assignee,
            created_by=self.user,
            **extra,
        )
        try:
            task.save()
        except ValidationError:
            raise
        record_event(self.project, self.user, "task.created", f"Created task {task.title}", task)
        return task

    def update_task(self, task: Task, **data) -> Task:
        self.require_project_member(self.project)
        ensure_project_writable(self.project)
        is_advisor = self.project.memberships.filter(
            user=self.user, status="active", role__in=["advisor", "reviewer"]
        ).exists()
        is_assignee = task.assignee_id == self.user.id
        if not (is_advisor or is_assignee):
            raise PermissionDenied("Only advisors or assigned students can update this task")
        advisor_only_fields = {
            "title",
            "description",
            "assignee",
            "assignee_id",
            "parent_task",
            "parent_task_id",
            "priority",
            "deadline_at",
        }
        if not is_advisor and advisor_only_fields.intersection(data):
            raise PermissionDenied("Only advisors can change task planning fields")
        old_status = task.status
        for field, value in data.items():
            setattr(task, field, value)
        if "status" in data and task.status == Task.Status.COMPLETED:
            task.completed_at = timezone.now()
        task.save()
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
