from pathlib import PurePath

from django.core.exceptions import PermissionDenied
from django.db import transaction

from apps.audit.services import record_event, record_upload
from apps.common.file_services import store_uploaded_file
from apps.common.models import UploadedFile
from apps.common.project_scope import ProjectScopedService
from apps.projects.archive_services import ensure_project_writable

from .models import WritingProject, WritingVersion


def _file_kind(filename: str) -> str:
    suffix = PurePath(filename).suffix.lower()
    if suffix in {".doc", ".docx"}:
        return WritingVersion.FileKind.WORD
    if suffix == ".tex":
        return WritingVersion.FileKind.LATEX_SOURCE
    return WritingVersion.FileKind.LATEX_ARCHIVE


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
            student=self.user,
            title=title,
            writing_type=writing_type,
        )
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
