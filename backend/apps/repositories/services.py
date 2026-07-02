from django.core.exceptions import ValidationError
from django.db import transaction

from apps.audit.services import record_event
from apps.projects.archive_services import ensure_project_writable

from .models import CodeArtifact, CodeArtifactVersion
from .upload_policy import validate_code_upload


class CodeArtifactService:
    def __init__(self, user, project):
        self.user = user
        self.project = project

    def _require_member(self):
        if not self.project.memberships.filter(user=self.user, status="active").exists():
            raise ValidationError("You are not a member of this project")

    @transaction.atomic
    def create_artifact(self, *, name: str, description: str = "", tags=None) -> CodeArtifact:
        self._require_member()
        ensure_project_writable(self.project)
        artifact = CodeArtifact.objects.create(
            project=self.project,
            name=name,
            description=description,
            tags=tags or [],
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
    def upload_version(
        self,
        artifact: CodeArtifact,
        *,
        filename: str,
        checksum_sha256: str,
        version_label: str = "",
        commit_reference: str = "",
        release_notes: str = "",
        content_type: str = "application/octet-stream",
        size_bytes: int = 0,
    ) -> CodeArtifactVersion:
        self._require_member()
        ensure_project_writable(self.project)
        if artifact.project_id != self.project.id:
            raise ValidationError("Code artifact does not belong to this project")
        if not version_label and not commit_reference:
            raise ValidationError("Version label or commit reference is required")
        validate_code_upload(filename=filename, content_type=content_type, size_bytes=size_bytes)
        versions = CodeArtifactVersion.objects.filter(project=self.project)
        if version_label and versions.filter(version_label=version_label).exists():
            raise ValidationError("Version label already exists in this project")
        if commit_reference and versions.filter(commit_reference=commit_reference).exists():
            raise ValidationError("Commit reference already exists in this project")
        if versions.filter(checksum_sha256=checksum_sha256).exists():
            raise ValidationError("Code artifact checksum already exists in this project")
        version = CodeArtifactVersion.objects.create(
            artifact=artifact,
            project=self.project,
            version_label=version_label,
            commit_reference=commit_reference,
            release_notes=release_notes,
            storage_key=f"code/{self.project.id}/{filename}",
            filename=filename,
            content_type=content_type,
            size_bytes=size_bytes,
            checksum_sha256=checksum_sha256,
            uploaded_by=self.user,
        )
        record_event(
            self.project,
            self.user,
            "code_artifact_version.uploaded",
            f"Uploaded code version {version.id}",
            version,
        )
        return version
