from pathlib import PurePath

from django.core.exceptions import PermissionDenied, ValidationError
from django.db import transaction

from apps.audit.boundary_events import record_boundary_event
from apps.audit.models import DownloadEvent
from apps.audit.services import record_event, record_upload
from apps.common.file_services import store_uploaded_file
from apps.common.models import UploadedFile
from apps.common.project_scope import ProjectScopedService
from apps.projects.archive_services import ensure_project_writable

from .models import WritingParticipant, WritingProject, WritingVersion
from .writing_participant_services import (
    anchor_project_for_standalone_writing,
    can_review_writing_project,
    ensure_default_writing_participants,
    participant_role_for,
    require_student_author,
)


def _file_kind(filename: str) -> str:
    suffix = PurePath(filename).suffix.lower()
    if suffix in {".doc", ".docx"}:
        return WritingVersion.FileKind.WORD
    if suffix == ".tex":
        return WritingVersion.FileKind.LATEX_SOURCE
    return WritingVersion.FileKind.LATEX_ARCHIVE


def _can_manage_writing_project(user, writing_project: WritingProject) -> bool:
    role = participant_role_for(user, writing_project)
    return role in {
        WritingParticipant.Role.STUDENT_AUTHOR,
        WritingParticipant.Role.ADMINISTRATOR,
    }


def _require_manage_writing_project(user, writing_project: WritingProject) -> None:
    if not _can_manage_writing_project(user, writing_project):
        raise PermissionDenied("Only the student author can manage this writing project")
    if writing_project.status == WritingProject.Status.ARCHIVED:
        raise PermissionDenied("Archived writing projects cannot be changed")


def rename_writing_project(user, writing_project: WritingProject, *, title: str) -> WritingProject:
    _require_manage_writing_project(user, writing_project)
    ensure_project_writable(writing_project.project)
    normalized_title = title.strip()
    if not normalized_title:
        raise ValidationError("Writing project title is required")
    writing_project.title = normalized_title
    writing_project.save(update_fields=["title", "updated_at"])
    record_event(
        writing_project.project,
        user,
        "writing_project.renamed",
        f"Renamed writing project {writing_project.id}",
        writing_project,
    )
    record_boundary_event(
        actor=user,
        resource=writing_project,
        boundary_type="standalone_writing",
        visibility_state="not_applicable",
        source_project=writing_project.legacy_project or writing_project.project,
        action="rename",
        outcome="success",
    )
    return writing_project


def archive_writing_project(user, writing_project: WritingProject) -> None:
    _require_manage_writing_project(user, writing_project)
    ensure_project_writable(writing_project.project)
    writing_project.status = WritingProject.Status.ARCHIVED
    writing_project.save(update_fields=["status", "updated_at"])
    record_event(
        writing_project.project,
        user,
        "writing_project.archived",
        f"Archived writing project {writing_project.id}",
        writing_project,
    )
    record_boundary_event(
        actor=user,
        resource=writing_project,
        boundary_type="standalone_writing",
        visibility_state="not_applicable",
        source_project=writing_project.legacy_project or writing_project.project,
        action="archive",
        outcome="success",
    )


class WritingProjectService(ProjectScopedService):
    def __init__(self, user, project):
        super().__init__(user)
        self.project = project

    def _require_student_member(self):
        if not self.project.memberships.filter(
            user=self.user, status="active", role="student"
        ).exists():
            raise PermissionDenied("Only project students can manage writing projects")

    def create_project(self, *, title: str, writing_type: str) -> WritingProject:
        self.require_project_member(self.project)
        ensure_project_writable(self.project)
        self._require_student_member()
        writing_project = WritingProject.objects.create(
            project=self.project,
            legacy_project=self.project,
            student=self.user,
            title=title,
            writing_type=writing_type,
        )
        ensure_default_writing_participants(writing_project)
        record_event(
            self.project,
            self.user,
            "writing_project.created",
            f"Created writing project {writing_project.title}",
            writing_project,
        )
        return writing_project

    @transaction.atomic
    def upload_version(
        self, *, writing_project: WritingProject, upload, summary: str = ""
    ) -> WritingVersion:
        self.require_project_member(self.project)
        ensure_project_writable(self.project)
        if writing_project.project_id != self.project.id:
            raise PermissionDenied("Writing project does not belong to this project")
        if writing_project.student_id != self.user.id:
            raise PermissionDenied("Only the writing project student can upload versions")
        if writing_project.status != WritingProject.Status.ACTIVE:
            raise PermissionDenied("Closed writing projects cannot receive new versions")

        locked_project = WritingProject.objects.select_for_update().get(pk=writing_project.pk)
        latest = locked_project.versions.order_by("-version_number").first()
        uploaded_file = store_uploaded_file(
            upload=upload,
            category=UploadedFile.Category.WRITING,
            owner=self.user,
        )
        version = WritingVersion.objects.create(
            writing_project=locked_project,
            version_number=(latest.version_number + 1 if latest else 1),
            submitted_by=self.user,
            draft_file=uploaded_file,
            file_kind=_file_kind(uploaded_file.original_filename),
            summary=summary,
        )
        record_upload(self.project, self.user, version, "writing_version")
        record_event(
            self.project,
            self.user,
            "writing_version.uploaded",
            f"Uploaded writing version {version.version_number}",
            version,
        )
        return version


@transaction.atomic
def create_standalone_writing_project(user, *, title: str, writing_type: str) -> WritingProject:
    project = anchor_project_for_standalone_writing(user)
    ensure_project_writable(project)
    writing_project = WritingProject.objects.create(
        project=project,
        legacy_project=project,
        student=user,
        title=title,
        writing_type=writing_type,
        migrated_from_project_nested_area=False,
    )
    ensure_default_writing_participants(writing_project)
    record_event(
        project,
        user,
        "writing_project.created",
        f"Created standalone writing project {writing_project.title}",
        writing_project,
    )
    record_boundary_event(
        actor=user,
        resource=writing_project,
        boundary_type="standalone_writing",
        visibility_state="not_applicable",
        source_project=project,
        action="create",
        outcome="success",
    )
    return writing_project


@transaction.atomic
def upload_standalone_writing_version(
    user, *, writing_project: WritingProject, upload, summary: str = ""
) -> WritingVersion:
    require_student_author(user, writing_project)
    ensure_project_writable(writing_project.project)
    if writing_project.status != WritingProject.Status.ACTIVE:
        raise PermissionDenied("Closed writing projects cannot receive new versions")

    locked_project = WritingProject.objects.select_for_update().get(pk=writing_project.pk)
    latest = locked_project.versions.order_by("-version_number").first()
    uploaded_file = store_uploaded_file(
        upload=upload,
        category=UploadedFile.Category.WRITING,
        owner=user,
    )
    version = WritingVersion.objects.create(
        writing_project=locked_project,
        version_number=(latest.version_number + 1 if latest else 1),
        submitted_by=user,
        draft_file=uploaded_file,
        file_kind=_file_kind(uploaded_file.original_filename),
        summary=summary,
    )
    record_upload(locked_project.project, user, version, "writing_version")
    record_event(
        locked_project.project,
        user,
        "writing_version.uploaded",
        f"Uploaded writing version {version.version_number}",
        version,
    )
    record_boundary_event(
        actor=user,
        resource=locked_project,
        boundary_type="standalone_writing",
        visibility_state="not_applicable",
        source_project=locked_project.legacy_project or locked_project.project,
        action="upload",
        outcome="success",
        metadata={"versionId": version.id},
    )
    return version


def require_writing_version_download_access(user, version: WritingVersion) -> None:
    writing_project = version.writing_project
    if not participant_role_for(user, writing_project):
        record_boundary_event(
            actor=user,
            resource=None,
            boundary_type="standalone_writing",
            visibility_state="not_applicable",
            source_project=writing_project.project,
            action="download",
            outcome="denied",
            metadata={"writingVersionId": version.id, "redaction": "[masked]"},
        )
        raise PermissionDenied("You are not authorized to download this writing version")


@transaction.atomic
def record_writing_version_download(user, version: WritingVersion) -> dict:
    require_writing_version_download_access(user, version)
    writing_project = version.writing_project
    if (
        can_review_writing_project(user, writing_project)
        and version.status == WritingVersion.Status.SUBMITTED
    ):
        version.status = WritingVersion.Status.UNDER_REVIEW
        version.save(update_fields=["status"])
    event = DownloadEvent.objects.create(
        project=writing_project.project,
        actor=user,
        target_type="writing_version_uploaded_file",
        target_id=str(version.draft_file_id),
        filename=version.draft_file.original_filename,
        checksum_sha256=version.draft_file.checksum_sha256,
        delivery_mode=DownloadEvent.DeliveryMode.DIRECT_RESPONSE,
    )
    record_event(
        writing_project.project,
        user,
        "writing_version.downloaded",
        f"Downloaded writing version file {version.draft_file_id}",
        event,
    )
    record_boundary_event(
        actor=user,
        resource=writing_project,
        boundary_type="standalone_writing",
        visibility_state="not_applicable",
        source_project=writing_project.legacy_project or writing_project.project,
        action="download",
        outcome="success",
        metadata={"writingVersionId": version.id},
    )
    return {
        "filename": version.draft_file.original_filename,
        "deliveryMode": "direct_response",
    }
