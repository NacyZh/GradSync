from django.core.exceptions import PermissionDenied
from django.db import transaction
from django.utils import timezone

from apps.audit.models import DownloadEvent
from apps.audit.services import record_event, record_feedback_event
from apps.common.file_services import store_uploaded_file
from apps.common.models import UploadedFile
from apps.common.project_scope import ProjectScopedService
from apps.notifications.models import Notification
from apps.projects.archive_services import ensure_project_writable

from .models import TeacherFeedback, WritingVersion


def _download_descriptor(filename: str) -> dict:
    return {
        "filename": filename,
        "deliveryMode": "direct_response",
        "url": "",
        "expiresAt": timezone.now().isoformat().replace("+00:00", "Z"),
    }


class TeacherFeedbackService(ProjectScopedService):
    def __init__(self, user, project):
        super().__init__(user)
        self.project = project

    @transaction.atomic
    def submit_feedback(
        self, *, writing_version: WritingVersion, annotated_file, comments: str = ""
    ) -> TeacherFeedback:
        self.require_project_reviewer(self.project)
        ensure_project_writable(self.project)
        if writing_version.writing_project.project_id != self.project.id:
            raise PermissionDenied("Writing version does not belong to this project")

        uploaded_file = store_uploaded_file(
            upload=annotated_file,
            category=UploadedFile.Category.FEEDBACK,
            owner=self.user,
        )
        notification = Notification.objects.create(
            project=self.project,
            recipient=writing_version.writing_project.student,
            sender=self.user,
            event_type=Notification.EventType.TEACHER_FEEDBACK,
            target_type="TeacherFeedback",
            target_id=str(writing_version.id),
            subject=f"Feedback available: {writing_version.writing_project.title}",
            action_path=(
                f"/projects/{self.project.id}/writing"
                f"?writingProjectId={writing_version.writing_project_id}"
            ),
            eligible_at=timezone.now(),
        )
        feedback = TeacherFeedback.objects.create(
            writing_version=writing_version,
            reviewer=self.user,
            comments=comments,
            annotated_file=uploaded_file,
            notification=notification,
            status=TeacherFeedback.Status.NOTIFICATION_PENDING,
        )
        writing_version.status = WritingVersion.Status.FEEDBACK_AVAILABLE
        writing_version.save(update_fields=["status"])
        record_feedback_event(self.project, self.user, feedback, "submitted")
        record_event(
            self.project,
            self.user,
            "writing_feedback.notification_pending",
            f"Queued writing feedback notification {notification.id}",
            notification,
        )
        return feedback

    def describe_feedback_download(self, feedback: TeacherFeedback) -> dict:
        writing_project = feedback.writing_version.writing_project
        if writing_project.project_id != self.project.id:
            raise PermissionDenied("Feedback does not belong to this project")
        is_owner = writing_project.student_id == self.user.id
        is_reviewer = self.project.memberships.filter(
            user=self.user, status="active", role__in=["advisor", "reviewer"]
        ).exists()
        if not (is_owner or is_reviewer or getattr(self.user, "is_administrator", False)):
            raise PermissionDenied("You are not authorized to download this feedback")

        event = DownloadEvent.objects.create(
            project=self.project,
            actor=self.user,
            target_type="teacher_feedback_uploaded_file",
            target_id=str(feedback.annotated_file_id),
            filename=feedback.annotated_file.original_filename,
            checksum_sha256=feedback.annotated_file.checksum_sha256,
            delivery_mode=DownloadEvent.DeliveryMode.DIRECT_RESPONSE,
        )
        record_event(
            self.project,
            self.user,
            "teacher_feedback.downloaded",
            f"Downloaded teacher feedback file {feedback.annotated_file_id}",
            event,
        )
        return _download_descriptor(feedback.annotated_file.original_filename)
