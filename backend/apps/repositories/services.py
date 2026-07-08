from dataclasses import dataclass

from django.core.exceptions import ValidationError
from django.core.files.storage import default_storage
from django.db import transaction
from django.utils import timezone

from apps.audit.services import record_event, record_upload
from apps.common.file_services import checksum_sha256, store_uploaded_file
from apps.projects.archive_services import ensure_project_writable

from .models import CodeArtifact, CodeArtifactVersion
from .upload_policy import validate_code_import

SEEDED_CODE_SAMPLE_NAME = "Simulator"
SEEDED_CODE_SAMPLE_SOURCE_PATH_LABEL = "team-library/code/simulator"
SEEDED_CODE_SAMPLE_STORAGE_KEY = "e2e/sim.zip"
SEEDED_CODE_SAMPLE_FILENAME = "sim.zip"
SEEDED_CODE_SAMPLE_CHECKSUM_SHA256 = "b" * 64
SEEDED_CODE_SAMPLE_IDENTITIES = (
    {
        "name": SEEDED_CODE_SAMPLE_NAME,
        "source_path_label": SEEDED_CODE_SAMPLE_SOURCE_PATH_LABEL,
        "storage_key": SEEDED_CODE_SAMPLE_STORAGE_KEY,
        "filename": SEEDED_CODE_SAMPLE_FILENAME,
        "checksum_sha256": SEEDED_CODE_SAMPLE_CHECKSUM_SHA256,
    },
    {
        "name": "Materials simulator",
        "source_path_label": "team-code/materials-simulator",
        "storage_key": "validation/code/materials-simulator.zip",
        "filename": "materials-simulator.zip",
        "checksum_sha256": "e" * 64,
    },
)


@dataclass(frozen=True)
class SeededCodeCleanupResult:
    matched: int
    removed: int


def _can_share_group_wide(user) -> bool:
    return bool(
        getattr(user, "is_superuser", False)
        or getattr(user, "is_administrator", False)
        or getattr(user, "is_advisor", False)
    )


def can_manage_code_artifact(user, artifact: CodeArtifact) -> bool:
    if not user or not getattr(user, "is_authenticated", False):
        return False
    if artifact.status != CodeArtifact.Status.ACTIVE:
        return False
    if artifact.project.status != "active":
        return False
    if getattr(user, "is_superuser", False) or getattr(user, "is_administrator", False):
        return True
    return artifact.project.advisor_id == getattr(user, "id", None)


def record_rejected_code_artifact_management_attempt(project, actor, artifact, action: str):
    return record_event(
        project,
        actor,
        f"code_artifact.{action}.rejected",
        f"Rejected code artifact {action} for {getattr(artifact, 'id', '')}",
        artifact,
    )


def is_seeded_code_sample(artifact: CodeArtifact) -> bool:
    versions = list(artifact.versions.all())
    if len(versions) != 1:
        return False
    version = versions[0]
    return any(
        artifact.name == identity["name"]
        and artifact.source_path_label == identity["source_path_label"]
        and version.storage_key == identity["storage_key"]
        and version.filename == identity["filename"]
        and version.checksum_sha256 == identity["checksum_sha256"]
        for identity in SEEDED_CODE_SAMPLE_IDENTITIES
    )


def remove_seeded_code_samples(*, dry_run: bool = False) -> SeededCodeCleanupResult:
    seed_names = [identity["name"] for identity in SEEDED_CODE_SAMPLE_IDENTITIES]
    seed_source_labels = [
        identity["source_path_label"] for identity in SEEDED_CODE_SAMPLE_IDENTITIES
    ]
    candidates = CodeArtifact.objects.filter(
        name__in=seed_names,
        source_path_label__in=seed_source_labels,
    ).prefetch_related("versions")
    matched = [artifact for artifact in candidates if is_seeded_code_sample(artifact)]
    if dry_run:
        return SeededCodeCleanupResult(matched=len(matched), removed=0)

    storage_keys = [
        version.storage_key
        for artifact in matched
        for version in artifact.versions.all()
        if version.storage_key
    ]
    storage_keys.extend(identity["storage_key"] for identity in SEEDED_CODE_SAMPLE_IDENTITIES)
    with transaction.atomic():
        removed = 0
        for artifact in matched:
            artifact.delete()
            removed += 1
    for storage_key in dict.fromkeys(storage_keys):
        if default_storage.exists(storage_key):
            default_storage.delete(storage_key)
    return SeededCodeCleanupResult(matched=len(matched), removed=removed)


class CodeArtifactService:
    def __init__(self, user, project):
        self.user = user
        self.project = project

    def _require_member(self):
        if getattr(self.user, "is_superuser", False) or getattr(
            self.user, "is_administrator", False
        ):
            return
        if self.project.advisor_id == getattr(self.user, "id", None):
            return
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
        if visibility == CodeArtifact.Visibility.GROUP_WIDE and not _can_share_group_wide(
            self.user
        ):
            raise PermissionError(
                "Only teachers and administrators can share code artifacts group-wide"
            )
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
        if visibility == CodeArtifact.Visibility.GROUP_WIDE and not _can_share_group_wide(
            self.user
        ):
            raise PermissionError(
                "Only teachers and administrators can share code artifacts group-wide"
            )

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

    def rename_artifact(
        self,
        artifact: CodeArtifact,
        *,
        name: str,
        reason: str = "",
    ) -> CodeArtifact:
        ensure_project_writable(self.project)
        if artifact.project_id != self.project.id:
            raise ValidationError("Code artifact does not belong to this project")
        if artifact.status != CodeArtifact.Status.ACTIVE:
            raise ValidationError("Code artifact is no longer active")
        if not can_manage_code_artifact(self.user, artifact):
            record_rejected_code_artifact_management_attempt(
                self.project, self.user, artifact, "rename"
            )
            raise PermissionError("You cannot rename this code artifact")

        cleaned_name = name.strip()
        if not cleaned_name:
            raise ValidationError("Code artifact name is required")
        duplicate_exists = CodeArtifact.objects.filter(
            project=self.project,
            name=cleaned_name,
            status=CodeArtifact.Status.ACTIVE,
        ).exclude(pk=artifact.pk).exists()
        if duplicate_exists:
            raise ValidationError("Active code artifact name already exists in this project")

        with transaction.atomic():
            artifact.name = cleaned_name
            artifact.save(update_fields=["name", "updated_at"])
            summary = f"Renamed code artifact {artifact.id}"
            if reason:
                summary = f"{summary}: {reason}"
            record_event(
                self.project,
                self.user,
                "code_artifact.renamed",
                summary,
                artifact,
            )
        return artifact

    def archive_artifact(self, artifact: CodeArtifact) -> None:
        ensure_project_writable(self.project)
        if artifact.project_id != self.project.id:
            raise ValidationError("Code artifact does not belong to this project")
        if artifact.status != CodeArtifact.Status.ACTIVE:
            raise ValidationError("Code artifact is no longer active")
        if not can_manage_code_artifact(self.user, artifact):
            record_rejected_code_artifact_management_attempt(
                self.project, self.user, artifact, "delete"
            )
            raise PermissionError("You cannot delete this code artifact")

        with transaction.atomic():
            artifact.status = CodeArtifact.Status.ARCHIVED
            artifact.archived_at = timezone.now()
            artifact.save(update_fields=["status", "archived_at", "updated_at"])
            record_event(
                self.project,
                self.user,
                "code_artifact.deleted",
                f"Deleted code artifact {artifact.id}",
                artifact,
            )
