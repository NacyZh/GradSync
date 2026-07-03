from django.conf import settings
from django.db import models


class PaperRecord(models.Model):
    class ImportSource(models.TextChoices):
        MANUAL = "manual", "Manual"
        LOCAL_FOLDER = "local_folder", "Local folder"
        LOCAL_FILE = "local_file", "Local file"
        BIBTEX = "bibtex", "BibTeX"
        TEXT_METADATA = "text_metadata", "Text metadata"
        BATCH = "batch", "Batch"

    class Status(models.TextChoices):
        ACTIVE = "active", "Active"
        DUPLICATE_BLOCKED = "duplicate_blocked", "Duplicate blocked"
        ARCHIVED = "archived", "Archived"

    class Visibility(models.TextChoices):
        PROJECT_MEMBERS = "project_members", "Project members"
        GROUP_WIDE = "group_wide", "Group-wide"

    project = models.ForeignKey(
        "projects.ResearchProject", on_delete=models.CASCADE, related_name="paper_records"
    )
    title = models.CharField(max_length=500)
    authors = models.JSONField(default=list, blank=True)
    venue = models.CharField(max_length=255, blank=True)
    publication_year = models.IntegerField(null=True, blank=True)
    doi = models.CharField(max_length=255, blank=True)
    external_ids = models.JSONField(default=dict, blank=True)
    abstract = models.TextField(blank=True)
    notes = models.TextField(blank=True)
    tags = models.JSONField(default=list, blank=True)
    visibility = models.CharField(
        max_length=30, choices=Visibility.choices, default=Visibility.PROJECT_MEMBERS
    )
    visibility_changed_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="paper_visibility_changes",
    )
    visibility_changed_at = models.DateTimeField(null=True, blank=True)
    uploaded_file = models.ForeignKey(
        "common.UploadedFile",
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        related_name="paper_records",
    )
    checksum_sha256 = models.CharField(max_length=64, blank=True, db_index=True)
    import_source = models.CharField(
        max_length=30, choices=ImportSource.choices, default=ImportSource.MANUAL
    )
    source_path_label = models.CharField(max_length=500, blank=True)
    fingerprint = models.CharField(max_length=600, blank=True)
    created_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT)
    status = models.CharField(max_length=30, choices=Status.choices, default=Status.ACTIVE)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    archived_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ["title"]
        indexes = [
            models.Index(fields=["project", "visibility", "status"], name="library_paper_scope_idx"),
            models.Index(fields=["project", "publication_year"], name="library_paper_year_idx"),
            models.Index(fields=["project", "title"], name="library_paper_title_idx"),
            models.Index(fields=["created_by", "created_at"], name="library_paper_uploader_idx"),
        ]


class PaperAttachment(models.Model):
    class Status(models.TextChoices):
        ACTIVE = "active", "Active"
        REPLACED = "replaced", "Replaced"
        ARCHIVED = "archived", "Archived"

    paper = models.ForeignKey(PaperRecord, on_delete=models.CASCADE, related_name="attachments")
    project = models.ForeignKey(
        "projects.ResearchProject", on_delete=models.CASCADE, related_name="paper_attachments"
    )
    storage_key = models.CharField(max_length=500)
    filename = models.CharField(max_length=255)
    relative_path = models.CharField(max_length=500, blank=True)
    content_type = models.CharField(max_length=120, blank=True)
    size_bytes = models.PositiveBigIntegerField(default=0)
    checksum_sha256 = models.CharField(max_length=64)
    imported_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT)
    status = models.CharField(max_length=20, choices=Status.choices, default=Status.ACTIVE)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]


class PaperImportBatch(models.Model):
    class SourceType(models.TextChoices):
        LOCAL_FOLDER = "local_folder", "Local folder"
        LOCAL_FILE = "local_file", "Local file"
        BIBTEX_FILE = "bibtex_file", "BibTeX file"
        TEXT_METADATA_FILE = "text_metadata_file", "Text metadata file"
        MIXED_LOCAL = "mixed_local", "Mixed local"

    class Status(models.TextChoices):
        STAGED = "staged", "Staged"
        COMMITTED = "committed", "Committed"
        FAILED = "failed", "Failed"
        CANCELLED = "cancelled", "Cancelled"

    project = models.ForeignKey(
        "projects.ResearchProject", on_delete=models.CASCADE, related_name="paper_import_batches"
    )
    requested_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT)
    source_type = models.CharField(max_length=20, choices=SourceType.choices)
    source_path_label = models.CharField(max_length=500, blank=True)
    status = models.CharField(max_length=20, choices=Status.choices, default=Status.STAGED)
    total_items = models.PositiveIntegerField(default=0)
    accepted_count = models.PositiveIntegerField(default=0)
    duplicate_count = models.PositiveIntegerField(default=0)
    error_count = models.PositiveIntegerField(default=0)
    result_summary = models.JSONField(default=list, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    committed_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ["-created_at"]
