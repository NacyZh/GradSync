from django.conf import settings
from django.core.exceptions import ValidationError
from django.db import models


class Task(models.Model):
    class Status(models.TextChoices):
        NOT_STARTED = "not_started", "Not started"
        IN_PROGRESS = "in_progress", "In progress"
        BLOCKED = "blocked", "Blocked"
        SUBMITTED = "submitted", "Submitted"
        COMPLETED = "completed", "Completed"
        CANCELLED = "cancelled", "Cancelled"

    class Priority(models.TextChoices):
        LOW = "low", "Low"
        NORMAL = "normal", "Normal"
        HIGH = "high", "High"
        URGENT = "urgent", "Urgent"

    project = models.ForeignKey(
        "projects.ResearchProject", on_delete=models.CASCADE, related_name="tasks"
    )
    parent_task = models.ForeignKey(
        "self", on_delete=models.CASCADE, null=True, blank=True, related_name="children"
    )
    title = models.CharField(max_length=255)
    description = models.TextField(blank=True)
    assignee = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True
    )
    assignees = models.ManyToManyField(
        settings.AUTH_USER_MODEL, blank=True, related_name="assigned_tasks"
    )
    status = models.CharField(max_length=20, choices=Status.choices, default=Status.NOT_STARTED)
    priority = models.CharField(max_length=20, choices=Priority.choices, default=Priority.NORMAL)
    deadline_at = models.DateTimeField(null=True, blank=True)
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.PROTECT, related_name="created_tasks"
    )
    completed_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["deadline_at", "id"]

    def clean(self):
        if self.parent_task and self.parent_task.project_id != self.project_id:
            raise ValidationError("Parent task must belong to the same project")
        if (
            self.parent_task
            and self.deadline_at
            and self.parent_task.deadline_at
            and self.deadline_at > self.parent_task.deadline_at
        ):
            raise ValidationError("Child task deadline cannot be later than parent deadline")
        seen = {self.pk}
        parent = self.parent_task
        while parent is not None:
            if parent.pk in seen:
                raise ValidationError("Task hierarchy cannot contain cycles")
            seen.add(parent.pk)
            parent = parent.parent_task
        if (
            self.assignee_id
            and not self.project.memberships.filter(
                user_id=self.assignee_id, status="active"
            ).exists()
        ):
            raise ValidationError("Assignee must be an active project member")

    def save(self, *args, **kwargs):
        self.full_clean()
        super().save(*args, **kwargs)

    def __str__(self) -> str:
        return self.title
