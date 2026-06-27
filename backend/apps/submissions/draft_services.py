from django.core.exceptions import PermissionDenied
from django.utils import timezone

from apps.audit.services import record_event
from apps.common.project_scope import ProjectScopedService
from apps.notifications.models import Notification
from apps.projects.archive_services import ensure_project_writable

from .models import Draft, DraftVersion


class DraftService(ProjectScopedService):
    def __init__(self, user, project):
        super().__init__(user)
        self.project = project

    def create_draft(self, *, title: str) -> Draft:
        self.require_project_member(self.project)
        ensure_project_writable(self.project)
        if not self.project.memberships.filter(
            user=self.user, status="active", role="student"
        ).exists():
            raise PermissionDenied("Only project students can submit drafts")
        draft = Draft.objects.create(project=self.project, student=self.user, title=title)
        record_event(
            self.project, self.user, "draft.created", f"Created draft {draft.title}", draft
        )
        return draft

    def submit_version(
        self, *, draft: Draft, content_reference: str, summary: str = ""
    ) -> DraftVersion:
        self.require_project_member(self.project)
        ensure_project_writable(self.project)
        if draft.student_id != self.user.id:
            raise PermissionDenied("Only the draft owner can submit a new version")
        if draft.status != Draft.Status.ACTIVE:
            raise PermissionDenied("Closed drafts cannot receive new versions")
        latest = draft.versions.order_by("-version_number").first()
        version = DraftVersion.objects.create(
            draft=draft,
            project=self.project,
            version_number=(latest.version_number + 1 if latest else 1),
            submitted_by=self.user,
            content_reference=content_reference,
            summary=summary,
        )
        for membership in self.project.memberships.filter(
            role__in=["advisor", "reviewer"], status="active"
        ):
            Notification.objects.create(
                project=self.project,
                recipient=membership.user,
                event_type=Notification.EventType.NEW_SUBMISSION,
                target_type="DraftVersion",
                target_id=str(version.id),
                subject=f"New draft submitted: {draft.title}",
                action_path=f"/projects/{self.project.id}/drafts/{draft.id}/versions/{version.id}",
                sender=self.user,
                eligible_at=timezone.now(),
            )
        record_event(
            self.project,
            self.user,
            "draft_version.submitted",
            f"Submitted draft version {version.version_number}",
            version,
        )
        return version

    def update_review_status(self, version: DraftVersion, review_status: str) -> DraftVersion:
        self.require_project_reviewer(self.project)
        ensure_project_writable(self.project)
        version.review_status = review_status
        version.reviewed_at = timezone.now()
        version.save(update_fields=["review_status", "reviewed_at"])
        record_event(
            self.project,
            self.user,
            "draft_version.reviewed",
            f"Set draft version {version.id} to {review_status}",
            version,
        )
        return version
