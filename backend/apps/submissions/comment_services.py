from django.core.exceptions import PermissionDenied, ValidationError
from django.utils import timezone

from apps.audit.services import record_event
from apps.common.project_scope import ProjectScopedService
from apps.projects.archive_services import ensure_project_writable

from .models import InlineComment, WeeklyProgressReport
from .review_assignment_services import reviewer_can_access_target


class InlineCommentService(ProjectScopedService):
    def __init__(self, user, project):
        super().__init__(user)
        self.project = project

    def create_comment(
        self, *, target_type: str, target_id: int, anchor: str, body: str
    ) -> InlineComment:
        ensure_project_writable(self.project)
        if target_type != InlineComment.TargetType.PROGRESS_REPORT:
            raise ValidationError("Inline comments are only supported for weekly reports")
        target = WeeklyProgressReport.objects.get(pk=target_id)
        if target.project_id != self.project.id:
            raise ValidationError("Comment target must belong to the same project")
        if not reviewer_can_access_target(user=self.user, target=target):
            raise PermissionDenied("You are not assigned to review this report")
        comment = InlineComment.objects.create(
            project=self.project,
            target_type=target_type,
            target_id=target_id,
            anchor=anchor,
            body=body,
            author=self.user,
        )
        record_event(
            self.project,
            self.user,
            "comment.created",
            f"Commented on {target_type} {target_id}",
            comment,
        )
        return comment

    def set_status(self, comment: InlineComment, status: str) -> InlineComment:
        ensure_project_writable(self.project)
        if comment.target_type != InlineComment.TargetType.PROGRESS_REPORT:
            raise PermissionDenied("You cannot update this comment")
        target = WeeklyProgressReport.objects.get(pk=comment.target_id)
        if not reviewer_can_access_target(user=self.user, target=target):
            raise PermissionDenied("You are not assigned to review this report")
        comment.status = status
        comment.resolved_at = timezone.now() if status == InlineComment.Status.RESOLVED else None
        comment.save(update_fields=["status", "resolved_at", "updated_at"])
        record_event(
            self.project,
            self.user,
            "comment.status_changed",
            f"Set comment {comment.id} to {status}",
            comment,
        )
        return comment
