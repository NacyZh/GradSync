from django.conf import settings
from django.db import models


class CodeArtifact(models.Model):
    class Visibility(models.TextChoices):
        PROJECT_MEMBERS = "project_members", "Project members"
        GROUP_WIDE = "group_wide", "Group-wide"

    class Status(models.TextChoices):
        ACTIVE = "active", "Active"
        SUPERSEDED = "superseded", "Superseded"
        ARCHIVED = "archived", "Archived"

    class BoundaryClassification(models.TextChoices):
        STANDALONE_SHARED = "standalone_shared", "Standalone shared"
        PROJECT_MATERIAL = "project_material", "Project material"
        PENDING_REVIEW = "pending_review", "Pending review"

    class ClassificationReason(models.TextChoices):
        PREVIOUS_FUNCTIONAL_AREA = "previous_functional_area", "Previous functional area"
        EXPLICIT_PROJECT_SPECIFIC = "explicit_project_specific", "Explicit project-specific"
        AMBIGUOUS_LEGACY = "ambiguous_legacy", "Ambiguous legacy"
        MANUAL_REVIEW = "manual_review", "Manual review"
        SYSTEM_DEFAULT = "system_default", "System default"

    project = models.ForeignKey(
        "projects.ResearchProject", on_delete=models.CASCADE, related_name="code_artifacts"
    )
    name = models.CharField(max_length=255)
    description = models.TextField(blank=True)
    tags = models.JSONField(default=list, blank=True)
    source_path_label = models.CharField(max_length=500, blank=True)
    visibility = models.CharField(
        max_length=30,
        choices=Visibility.choices,
        default=Visibility.PROJECT_MEMBERS,
    )
    visibility_changed_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="code_artifact_visibility_changes",
    )
    visibility_changed_at = models.DateTimeField(null=True, blank=True)
    boundary_classification = models.CharField(
        max_length=30,
        choices=BoundaryClassification.choices,
        default=BoundaryClassification.STANDALONE_SHARED,
        db_index=True,
    )
    source_project = models.ForeignKey(
        "projects.ResearchProject",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="source_code_artifacts",
    )
    migrated_from_project_nested_area = models.BooleanField(default=False)
    classification_reason = models.CharField(
        max_length=40,
        choices=ClassificationReason.choices,
        default=ClassificationReason.PREVIOUS_FUNCTIONAL_AREA,
    )
    archive_file = models.ForeignKey(
        "common.UploadedFile",
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        related_name="code_artifacts",
    )
    checksum_sha256 = models.CharField(max_length=64, blank=True, db_index=True)
    status = models.CharField(max_length=20, choices=Status.choices, default=Status.ACTIVE)
    created_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    archived_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ["name"]
        indexes = [
            models.Index(fields=["project", "visibility", "status"], name="repo_code_scope_idx"),
            models.Index(fields=["project", "name"], name="repo_code_name_idx"),
            models.Index(fields=["created_by", "created_at"], name="repo_code_uploader_idx"),
            models.Index(
                fields=["boundary_classification", "visibility", "status"],
                name="repo_code_boundary_idx",
            ),
            models.Index(
                fields=["source_project", "boundary_classification", "status"],
                name="repo_code_source_idx",
            ),
        ]


class CodeArtifactVersion(models.Model):
    class Status(models.TextChoices):
        ACTIVE = "active", "Active"
        SUPERSEDED = "superseded", "Superseded"
        ARCHIVED = "archived", "Archived"

    artifact = models.ForeignKey(CodeArtifact, on_delete=models.CASCADE, related_name="versions")
    project = models.ForeignKey(
        "projects.ResearchProject",
        on_delete=models.CASCADE,
        related_name="code_artifact_versions",
    )
    version_label = models.CharField(max_length=120, blank=True)
    commit_reference = models.CharField(max_length=255, blank=True)
    release_notes = models.TextField(blank=True)
    description = models.TextField(blank=True)
    storage_key = models.CharField(max_length=500)
    filename = models.CharField(max_length=255)
    relative_path_manifest = models.JSONField(default=list, blank=True)
    content_type = models.CharField(max_length=120, blank=True)
    size_bytes = models.PositiveBigIntegerField(default=0)
    checksum_sha256 = models.CharField(max_length=64)
    imported_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT)
    imported_at = models.DateTimeField(auto_now_add=True)
    status = models.CharField(max_length=20, choices=Status.choices, default=Status.ACTIVE)

    class Meta:
        ordering = ["-imported_at"]
