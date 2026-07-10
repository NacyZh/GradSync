from django.conf import settings
from django.db import models


class DocumentCategory(models.Model):
    class Status(models.TextChoices):
        ACTIVE = "active", "Active"
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

    name = models.CharField(max_length=120, unique=True)
    description = models.TextField(blank=True)
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name="document_categories",
    )
    status = models.CharField(max_length=20, choices=Status.choices, default=Status.ACTIVE)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["name"]
        indexes = [
            models.Index(fields=["status", "name"], name="library_doccat_status_idx"),
        ]

    def __str__(self) -> str:
        return self.name


class DocumentRecord(models.Model):
    class Visibility(models.TextChoices):
        PROJECT_MEMBERS = "project_members", "Project members"
        GROUP_WIDE = "group_wide", "Group-wide"

    class Status(models.TextChoices):
        ACTIVE = "active", "Active"
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
        "projects.ResearchProject", on_delete=models.CASCADE, related_name="document_records"
    )
    visibility = models.CharField(
        max_length=30, choices=Visibility.choices, default=Visibility.PROJECT_MEMBERS
    )
    visibility_changed_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="document_visibility_changes",
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
        related_name="source_document_records",
    )
    migrated_from_project_nested_area = models.BooleanField(default=False)
    classification_reason = models.CharField(
        max_length=40,
        choices=ClassificationReason.choices,
        default=ClassificationReason.PREVIOUS_FUNCTIONAL_AREA,
    )
    category = models.ForeignKey(
        DocumentCategory, on_delete=models.PROTECT, related_name="documents"
    )
    title = models.CharField(max_length=255)
    description = models.TextField(blank=True)
    document_file = models.ForeignKey(
        "common.UploadedFile",
        on_delete=models.PROTECT,
        related_name="document_records",
    )
    checksum_sha256 = models.CharField(max_length=64, db_index=True)
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name="document_records",
    )
    status = models.CharField(max_length=20, choices=Status.choices, default=Status.ACTIVE)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["title"]
        indexes = [
            models.Index(fields=["project", "visibility", "status"], name="library_doc_scope_idx"),
            models.Index(fields=["project", "category", "title"], name="library_doc_category_idx"),
            models.Index(fields=["created_by", "created_at"], name="library_doc_uploader_idx"),
            models.Index(
                fields=["boundary_classification", "visibility", "status"],
                name="library_doc_boundary_idx",
            ),
            models.Index(
                fields=["source_project", "boundary_classification", "status"],
                name="library_doc_source_idx",
            ),
        ]
