from django.core.exceptions import PermissionDenied
from django.db import transaction
from django.utils import timezone

from apps.audit.boundary_events import record_boundary_event
from apps.audit.models import DownloadEvent
from apps.audit.services import record_event, record_feedback_event
from apps.common.file_services import store_uploaded_file
from apps.common.models import UploadedFile
from apps.common.project_scope import ProjectScopedService
from apps.notifications.models import Notification
from apps.projects.archive_services import ensure_project_writable

from .models import TeacherFeedback, WritingVersion
from .writing_participant_services import can_review_writing_project, participant_role_for


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
        ensure_project_writable(self.project)
        if writing_version.writing_project.project_id != self.project.id:
            raise PermissionDenied("Writing version does not belong to this project")
        if not can_review_writing_project(self.user, writing_version.writing_project):
            record_boundary_event(
                actor=self.user,
                resource=None,
                boundary_type="standalone_writing",
                visibility_state="not_applicable",
                source_project=self.project,
                action="feedback_submit",
                outcome="denied",
                metadata={"writingVersionId": writing_version.id},
            )
            raise PermissionDenied("You are not authorized to submit feedback")

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
            action_path=f"/writing?writingProjectId={writing_version.writing_project_id}",
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
        record_boundary_event(
            actor=self.user,
            resource=writing_version.writing_project,
            boundary_type="standalone_writing",
            visibility_state="not_applicable",
            source_project=writing_version.writing_project.legacy_project
            or writing_version.writing_project.project,
            action="feedback_submit",
            outcome="success",
            metadata={"writingVersionId": writing_version.id, "feedbackId": feedback.id},
        )
        return feedback

    def describe_feedback_download(self, feedback: TeacherFeedback) -> dict:
        writing_project = feedback.writing_version.writing_project
        if writing_project.project_id != self.project.id:
            raise PermissionDenied("Feedback does not belong to this project")
        role = participant_role_for(self.user, writing_project)
        if not role:
            record_boundary_event(
                actor=self.user,
                resource=None,
                boundary_type="standalone_writing",
                visibility_state="not_applicable",
                source_project=self.project,
                action="download",
                outcome="denied",
                metadata={"feedbackId": feedback.id, "redaction": "[masked]"},
            )
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
        record_boundary_event(
            actor=self.user,
            resource=writing_project,
            boundary_type="standalone_writing",
            visibility_state="not_applicable",
            source_project=writing_project.legacy_project or writing_project.project,
            action="download",
            outcome="success",
            metadata={"feedbackId": feedback.id},
        )
        return _download_descriptor(feedback.annotated_file.original_filename)
