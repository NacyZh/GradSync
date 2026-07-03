from django.core.exceptions import ValidationError
from django.db import transaction
from django.utils import timezone

from apps.audit.services import record_event, record_upload
from apps.common.file_services import checksum_sha256, store_uploaded_file
from apps.projects.archive_services import ensure_project_writable

from .models import CodeArtifact, CodeArtifactVersion
from .upload_policy import validate_code_import


def _can_share_group_wide(user) -> bool:
    return bool(
        getattr(user, "is_superuser", False)
        or getattr(user, "is_administrator", False)
        or getattr(user, "is_advisor", False)
    )


class CodeArtifactService:
    def __init__(self, user, project):
        self.user = user
        self.project = project

    def _require_member(self):
        if not self.project.memberships.filter(user=self.user, status="active").exists():
            raise ValidationError("You are not a member of this project")

    @transaction.atomic
    def create_artifact(
        self,
        *,
        name: str,
        description: str = "",
        tags=None,
        source_path_label: str = "",
        visibility: str = CodeArtifact.Visibility.PROJECT_MEMBERS,
    ) -> CodeArtifact:
        self._require_member()
        ensure_project_writable(self.project)
        if visibility == CodeArtifact.Visibility.GROUP_WIDE and not _can_share_group_wide(self.user):
            raise PermissionError("Only teachers and administrators can share code artifacts group-wide")
        artifact = CodeArtifact.objects.create(
            project=self.project,
            name=name,
            description=description,
            tags=tags or [],
            source_path_label=source_path_label,
            visibility=visibility,
            visibility_changed_by=self.user,
            visibility_changed_at=timezone.now(),
            created_by=self.user,
        )
        record_event(
            self.project,
            self.user,
            "code_artifact.created",
            f"Created code artifact {artifact.id}",
            artifact,
        )
        return artifact

    @transaction.atomic
    def upload_archive(
        self,
        *,
        upload,
        name: str,
        description: str,
        tags=None,
        visibility: str = CodeArtifact.Visibility.PROJECT_MEMBERS,
    ) -> CodeArtifact:
        self._require_member()
        ensure_project_writable(self.project)
        if not description or not description.strip():
            raise ValidationError("Code artifact description is required")
        if visibility == CodeArtifact.Visibility.GROUP_WIDE and not _can_share_group_wide(self.user):
            raise PermissionError("Only teachers and administrators can share code artifacts group-wide")

        checksum = checksum_sha256(upload)
        if CodeArtifact.objects.filter(
            project=self.project,
            checksum_sha256=checksum,
            status=CodeArtifact.Status.ACTIVE,
        ).exists():
            raise ValidationError("Code artifact checksum already exists in this project")

        uploaded_file = store_uploaded_file(upload=upload, category="code", owner=self.user)
        artifact = CodeArtifact.objects.create(
            project=self.project,
            name=name,
            description=description,
            tags=tags or [],
            source_path_label=uploaded_file.original_filename,
            visibility=visibility,
            visibility_changed_by=self.user,
            visibility_changed_at=timezone.now(),
            archive_file=uploaded_file,
            checksum_sha256=uploaded_file.checksum_sha256,
            created_by=self.user,
        )
        CodeArtifactVersion.objects.create(
            artifact=artifact,
            project=self.project,
            version_label="",
            description=description,
            storage_key=uploaded_file.stored_name,
            filename=uploaded_file.original_filename,
            relative_path_manifest=[uploaded_file.original_filename],
            content_type=uploaded_file.content_type,
            size_bytes=uploaded_file.size_bytes,
            checksum_sha256=uploaded_file.checksum_sha256,
            imported_by=self.user,
        )
        record_upload(self.project, self.user, artifact, "code_artifact")
        return artifact

    @transaction.atomic
    def import_version(
        self,
        artifact: CodeArtifact,
        *,
        filename: str,
        checksum_sha256: str,
        version_label: str = "",
        commit_reference: str = "",
        release_notes: str = "",
        description: str = "",
        source_type: str = "local_archive",
        source_path_label: str = "",
        relative_path_manifest=None,
        content_type: str = "application/octet-stream",
        size_bytes: int = 0,
    ) -> CodeArtifactVersion:
        self._require_member()
        ensure_project_writable(self.project)
        if artifact.project_id != self.project.id:
            raise ValidationError("Code artifact does not belong to this project")
        if not version_label and not commit_reference:
            raise ValidationError("Version label or commit reference is required")
        validate_code_import(filename=filename, content_type=content_type, size_bytes=size_bytes)
        versions = CodeArtifactVersion.objects.filter(project=self.project)
        if version_label and versions.filter(version_label=version_label).exists():
            raise ValidationError("Version label already exists in this project")
        if commit_reference and versions.filter(commit_reference=commit_reference).exists():
            raise ValidationError("Commit reference already exists in this project")
        if versions.filter(checksum_sha256=checksum_sha256).exists():
            raise ValidationError("Code artifact checksum already exists in this project")
        path_manifest = relative_path_manifest or ([source_path_label] if source_path_label else [])
        version = CodeArtifactVersion.objects.create(
            artifact=artifact,
            project=self.project,
            version_label=version_label,
            commit_reference=commit_reference,
            release_notes=release_notes,
            description=description,
            storage_key=f"code/{self.project.id}/{filename}",
            filename=filename,
            relative_path_manifest=path_manifest,
            content_type=content_type,
            size_bytes=size_bytes,
            checksum_sha256=checksum_sha256,
            imported_by=self.user,
        )
        record_event(
            self.project,
            self.user,
            "code_artifact_version.imported",
            f"Imported code version {version.id}",
            version,
        )
        return version
