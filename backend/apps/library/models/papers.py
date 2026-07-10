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
        PENDING_REVIEW = "pending_review", "Pending review"
        REJECTED = "rejected", "Rejected"
        DELETED = "deleted", "Deleted"
        INVALID = "invalid", "Invalid"
        DUPLICATE_BLOCKED = "duplicate_blocked", "Duplicate blocked"
        ARCHIVED = "archived", "Archived"

    class Visibility(models.TextChoices):
        PROJECT_MEMBERS = "project_members", "Project members"
        GROUP_WIDE = "group_wide", "Group-wide"

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
        related_name="source_paper_records",
    )
    migrated_from_project_nested_area = models.BooleanField(default=False)
    classification_reason = models.CharField(
        max_length=40,
        choices=ClassificationReason.choices,
        default=ClassificationReason.PREVIOUS_FUNCTIONAL_AREA,
    )
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
    canonical_title = models.CharField(max_length=500, blank=True)
    normalized_title = models.CharField(max_length=600, blank=True, db_index=True)
    title_source = models.CharField(
        max_length=40,
        choices=[
            ("embedded_metadata", "Embedded metadata"),
            ("first_page_visible_text", "First-page visible text"),
            ("legacy", "Legacy record"),
        ],
        blank=True,
    )
    title_confidence = models.CharField(
        max_length=20,
        choices=[
            ("high", "High"),
            ("medium", "Medium"),
            ("low", "Low"),
            ("failed", "Failed"),
        ],
        blank=True,
    )
    migrated_from_legacy_scope = models.BooleanField(default=False)
    shared_access_started_at = models.DateTimeField(null=True, blank=True)
    created_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT)
    status = models.CharField(max_length=30, choices=Status.choices, default=Status.ACTIVE)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    archived_at = models.DateTimeField(null=True, blank=True)
    deleted_at = models.DateTimeField(null=True, blank=True)
    deleted_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="deleted_paper_records",
    )
    delete_reason = models.CharField(max_length=255, blank=True)

    class Meta:
        ordering = ["title"]
        indexes = [
            models.Index(
                fields=["project", "visibility", "status"],
                name="library_paper_scope_idx",
            ),
            models.Index(fields=["project", "publication_year"], name="library_paper_year_idx"),
            models.Index(fields=["project", "title"], name="library_paper_title_idx"),
            models.Index(fields=["created_by", "created_at"], name="library_paper_uploader_idx"),
            models.Index(
                fields=["boundary_classification", "visibility", "status"],
                name="library_paper_boundary_idx",
            ),
            models.Index(
                fields=["source_project", "boundary_classification", "status"],
                name="library_paper_source_idx",
            ),
            models.Index(
                fields=["status", "normalized_title"],
                name="library_paper_shared_title_idx",
            ),
            models.Index(fields=["status", "title_source"], name="library_paper_title_source_idx"),
        ]

    def save(self, *args, **kwargs):
        if not self.canonical_title:
            self.canonical_title = self.title
        if not self.normalized_title:
            from ..services.duplicates import normalize_title

            self.normalized_title = normalize_title(self.canonical_title or self.title)
        super().save(*args, **kwargs)


class PaperFile(models.Model):
    class ValidationStatus(models.TextChoices):
        PENDING = "pending", "Pending"
        VALID = "valid", "Valid"
        INVALID = "invalid", "Invalid"

    class FailureReason(models.TextChoices):
        UNSUPPORTED_TYPE = "unsupported_type", "Unsupported type"
        EMPTY_FILE = "empty_file", "Empty file"
        CORRUPTED_PDF = "corrupted_pdf", "Corrupted PDF"
        PASSWORD_BLOCKED = "password_blocked", "Password blocked"
        OVERSIZED = "oversized", "Oversized"
        UNSAFE_PATH = "unsafe_path", "Unsafe path"
        UNKNOWN = "unknown", "Unknown"

    paper = models.ForeignKey(
        PaperRecord, on_delete=models.CASCADE, null=True, blank=True, related_name="paper_files"
    )
    uploaded_file = models.OneToOneField(
        "common.UploadedFile",
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        related_name="paper_file_record",
    )
    storage_key = models.CharField(max_length=500, blank=True)
    original_filename = models.CharField(max_length=255)
    default_download_filename = models.CharField(max_length=255, blank=True)
    content_type = models.CharField(max_length=120, blank=True)
    size_bytes = models.PositiveBigIntegerField(default=0)
    file_fingerprint = models.CharField(max_length=128, db_index=True)
    validation_status = models.CharField(
        max_length=20, choices=ValidationStatus.choices, default=ValidationStatus.PENDING
    )
    validation_failure_reason = models.CharField(
        max_length=40, choices=FailureReason.choices, blank=True
    )
    uploaded_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT)
    uploaded_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-uploaded_at"]
        indexes = [
            models.Index(fields=["file_fingerprint"], name="library_pfile_fingerprint_idx"),
            models.Index(fields=["uploaded_by", "uploaded_at"], name="library_pfile_uploader_idx"),
        ]


class PaperTitleExtractionResult(models.Model):
    class SourceAttempted(models.TextChoices):
        EMBEDDED_METADATA = "embedded_metadata", "Embedded metadata"
        FIRST_PAGE_VISIBLE_TEXT = "first_page_visible_text", "First-page visible text"

    class Confidence(models.TextChoices):
        HIGH = "high", "High"
        MEDIUM = "medium", "Medium"
        LOW = "low", "Low"
        FAILED = "failed", "Failed"

    class FailureReason(models.TextChoices):
        MISSING_TITLE = "missing_title", "Missing title"
        UNRELIABLE_TITLE = "unreliable_title", "Unreliable title"
        UNREADABLE_PDF = "unreadable_pdf", "Unreadable PDF"
        EXTRACTION_TIMEOUT = "extraction_timeout", "Extraction timeout"
        UNSUPPORTED_STRUCTURE = "unsupported_structure", "Unsupported structure"
        UNKNOWN = "unknown", "Unknown"

    paper_file = models.ForeignKey(
        PaperFile, on_delete=models.CASCADE, related_name="title_extraction_results"
    )
    source_attempted = models.CharField(max_length=40, choices=SourceAttempted.choices)
    extracted_title = models.CharField(max_length=500, blank=True)
    normalized_title = models.CharField(max_length=600, blank=True)
    extracted_authors = models.JSONField(default=list, blank=True)
    extracted_year = models.IntegerField(null=True, blank=True)
    extracted_keywords = models.JSONField(default=list, blank=True)
    confidence = models.CharField(max_length=20, choices=Confidence.choices)
    failure_reason = models.CharField(max_length=40, choices=FailureReason.choices, blank=True)
    started_at = models.DateTimeField(null=True, blank=True)
    completed_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ["-completed_at", "-id"]


class DuplicateDetectionResult(models.Model):
    class Decision(models.TextChoices):
        ACCEPTED_NEW = "accepted_new", "Accepted new"
        DUPLICATE_FILE_FINGERPRINT = "duplicate_file_fingerprint", "Duplicate file fingerprint"
        DUPLICATE_METADATA_STRONG_MATCH = (
            "duplicate_metadata_strong_match",
            "Duplicate metadata strong match",
        )
        MAINTAINER_REVIEW = "maintainer_review", "Maintainer review"
        REJECTED = "rejected", "Rejected"

    class MatchBasis(models.TextChoices):
        FILE_FINGERPRINT = "file_fingerprint", "File fingerprint"
        NORMALIZED_TITLE_AUTHOR_YEAR = (
            "normalized_title_author_year",
            "Normalized title author year",
        )
        FUZZY_TITLE_METADATA = "fuzzy_title_metadata", "Fuzzy title metadata"
        NONE = "none", "None"

    class ReviewStatus(models.TextChoices):
        NONE = "none", "None"
        PENDING = "pending", "Pending"
        CONFIRMED_DUPLICATE = "confirmed_duplicate", "Confirmed duplicate"
        CONFIRMED_DISTINCT = "confirmed_distinct", "Confirmed distinct"

    paper_file = models.ForeignKey(
        PaperFile, on_delete=models.CASCADE, related_name="duplicate_detection_results"
    )
    candidate_paper = models.ForeignKey(
        PaperRecord,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="duplicate_candidates",
    )
    decision = models.CharField(max_length=40, choices=Decision.choices)
    match_basis = models.CharField(max_length=40, choices=MatchBasis.choices)
    matched_title = models.CharField(max_length=500, blank=True)
    matched_authors = models.JSONField(default=list, blank=True)
    matched_year = models.IntegerField(null=True, blank=True)
    similarity_score = models.FloatField(null=True, blank=True)
    review_status = models.CharField(
        max_length=30, choices=ReviewStatus.choices, default=ReviewStatus.NONE
    )
    reviewed_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="paper_duplicate_reviews",
    )
    reviewed_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["decision", "review_status"], name="library_dup_decision_idx"),
        ]


class PaperImportJob(models.Model):
    class Status(models.TextChoices):
        UPLOADING = "uploading", "Uploading"
        VALIDATING = "validating", "Validating"
        EXTRACTING_TITLE = "extracting_title", "Extracting title"
        CHECKING_DUPLICATE = "checking_duplicate", "Checking duplicate"
        ACCEPTED = "accepted", "Accepted"
        DUPLICATE = "duplicate", "Duplicate"
        MAINTAINER_REVIEW = "maintainer_review", "Maintainer review"
        REJECTED = "rejected", "Rejected"
        FAILED = "failed", "Failed"

    class FailureReason(models.TextChoices):
        UNSUPPORTED_TYPE = "unsupported_type", "Unsupported type"
        EMPTY_FILE = "empty_file", "Empty file"
        CORRUPTED_PDF = "corrupted_pdf", "Corrupted PDF"
        PASSWORD_BLOCKED = "password_blocked", "Password blocked"
        OVERSIZED = "oversized", "Oversized"
        UNSAFE_PATH = "unsafe_path", "Unsafe path"
        MISSING_RELIABLE_TITLE = "missing_reliable_title", "Missing reliable title"
        DUPLICATE = "duplicate", "Duplicate"
        EXPIRED_SESSION = "expired_session", "Expired session"
        PROCESSING_ERROR = "processing_error", "Processing error"
        UNKNOWN = "unknown", "Unknown"

    paper_file = models.ForeignKey(
        PaperFile, on_delete=models.PROTECT, related_name="import_jobs", null=True, blank=True
    )
    requested_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT)
    status = models.CharField(max_length=30, choices=Status.choices, default=Status.UPLOADING)
    user_message = models.CharField(max_length=500, blank=True)
    failure_reason = models.CharField(max_length=40, choices=FailureReason.choices, blank=True)
    accepted_paper = models.ForeignKey(
        PaperRecord,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="accepted_import_jobs",
    )
    duplicate_paper = models.ForeignKey(
        PaperRecord,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="duplicate_import_jobs",
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    completed_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["requested_by", "status"], name="library_import_user_status_idx"),
            models.Index(fields=["status", "created_at"], name="library_import_status_idx"),
        ]


class PaperLibraryActivity(models.Model):
    class Action(models.TextChoices):
        UPLOAD_ACCEPTED = "upload_accepted", "Upload accepted"
        UPLOAD_REJECTED = "upload_rejected", "Upload rejected"
        UPLOAD_SIZE_REJECTED = "upload_size_rejected", "Upload size rejected"
        DUPLICATE_REJECTED = "duplicate_rejected", "Duplicate rejected"
        MAINTAINER_REVIEW_CREATED = "maintainer_review_created", "Maintainer review created"
        PAPER_RENAMED = "paper_renamed", "Paper renamed"
        PAPER_RENAME_REJECTED = "paper_rename_rejected", "Paper rename rejected"
        PAPER_DELETED = "paper_deleted", "Paper deleted"
        PAPER_DELETE_REJECTED = "paper_delete_rejected", "Paper delete rejected"
        DOWNLOAD_STARTED = "download_started", "Download started"
        DOWNLOAD_FAILED = "download_failed", "Download failed"
        UNAVAILABLE_ACCESS = "unavailable_access", "Unavailable access"
        MIGRATION_SHARED_ACCESS_APPLIED = (
            "migration_shared_access_applied",
            "Migration shared access applied",
        )

    class Outcome(models.TextChoices):
        SUCCESS = "success", "Success"
        REJECTED = "rejected", "Rejected"
        FAILED = "failed", "Failed"

    actor = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="paper_library_activities",
    )
    paper = models.ForeignKey(
        PaperRecord, on_delete=models.SET_NULL, null=True, blank=True, related_name="activities"
    )
    paper_file = models.ForeignKey(
        PaperFile, on_delete=models.SET_NULL, null=True, blank=True, related_name="activities"
    )
    import_job = models.ForeignKey(
        PaperImportJob,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="activities",
    )
    action = models.CharField(max_length=50, choices=Action.choices)
    outcome = models.CharField(max_length=20, choices=Outcome.choices)
    reason = models.CharField(max_length=255, blank=True)
    request_id = models.CharField(max_length=64, blank=True)
    occurred_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-occurred_at"]
        indexes = [
            models.Index(fields=["action", "occurred_at"], name="library_activity_action_idx"),
            models.Index(fields=["actor", "occurred_at"], name="library_activity_actor_idx"),
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
