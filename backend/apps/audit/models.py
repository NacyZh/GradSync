import uuid

from django.conf import settings
from django.db import models


class AuditEvent(models.Model):
    class Category(models.TextChoices):
        ACCOUNT_SECURITY = "account_security", "Account security"
        ACCOUNT_GOVERNANCE = "account_governance", "Account governance"
        PROJECT_GOVERNANCE = "project_governance", "Project governance"
        SUBMISSION_REVIEW = "submission_review", "Submission review"
        MATERIAL = "material", "Material"
        RESOURCE = "resource", "Resource"
        SCHEDULE = "schedule", "Schedule"
        NOTIFICATION = "notification", "Notification"
        AUDIT_ACCESS = "audit_access", "Audit access"
        RELEASE_GOVERNANCE = "release_governance", "Release governance"
        OTHER = "other", "Other"

    class Outcome(models.TextChoices):
        SUCCEEDED = "succeeded", "Succeeded"
        DENIED = "denied", "Denied"
        FAILED = "failed", "Failed"
        QUEUED = "queued", "Queued"

    project = models.ForeignKey(
        "projects.ResearchProject",
        on_delete=models.CASCADE,
        related_name="audit_events",
        null=True,
        blank=True,
    )
    actor = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True
    )
    event_type = models.CharField(max_length=80)
    target_type = models.CharField(max_length=80, blank=True)
    target_id = models.CharField(max_length=80, blank=True)
    target_snapshot = models.JSONField(default=dict, blank=True)
    category = models.CharField(max_length=40, choices=Category.choices, default=Category.OTHER)
    outcome = models.CharField(max_length=20, choices=Outcome.choices, default=Outcome.SUCCEEDED)
    reason = models.TextField(blank=True)
    correlation_id = models.CharField(max_length=64, blank=True, db_index=True)
    actor_snapshot = models.JSONField(default=dict, blank=True)
    redaction_version = models.PositiveSmallIntegerField(default=1)
    summary = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["-created_at", "-id"], name="audit_event_cursor_idx"),
            models.Index(fields=["category", "-created_at"], name="audit_event_category_idx"),
            models.Index(fields=["outcome", "-created_at"], name="audit_event_outcome_idx"),
            models.Index(fields=["actor", "-created_at"], name="audit_event_actor_idx"),
            models.Index(fields=["project", "-created_at"], name="audit_event_project_idx"),
            models.Index(
                fields=["target_type", "target_id", "-created_at"],
                name="audit_event_target_idx",
            ),
        ]


class DownloadEvent(models.Model):
    class DeliveryMode(models.TextChoices):
        DIRECT_RESPONSE = "direct_response", "Direct response"
        SIGNED_URL = "signed_url", "Signed URL"

    project = models.ForeignKey(
        "projects.ResearchProject", on_delete=models.CASCADE, related_name="download_events"
    )
    actor = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT)
    target_type = models.CharField(max_length=80)
    target_id = models.CharField(max_length=80)
    filename = models.CharField(max_length=255)
    checksum_sha256 = models.CharField(max_length=64)
    downloaded_at = models.DateTimeField(auto_now_add=True)
    delivery_mode = models.CharField(
        max_length=30, choices=DeliveryMode.choices, default=DeliveryMode.DIRECT_RESPONSE
    )

    class Meta:
        ordering = ["-downloaded_at"]


class AuditExport(models.Model):
    class Status(models.TextChoices):
        QUEUED = "queued", "Queued"
        PROCESSING = "processing", "Processing"
        READY = "ready", "Ready"
        FAILED = "failed", "Failed"
        EXPIRED = "expired", "Expired"

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    requested_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name="audit_exports",
    )
    status = models.CharField(max_length=20, choices=Status.choices, default=Status.QUEUED)
    filter_snapshot = models.JSONField(default=dict)
    high_water_event_id = models.PositiveBigIntegerField()
    requested_count = models.PositiveIntegerField()
    exported_count = models.PositiveIntegerField(default=0)
    file = models.ForeignKey(
        "common.UploadedFile",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="audit_exports",
    )
    checksum_sha256 = models.CharField(max_length=64, blank=True)
    failure_reason = models.CharField(max_length=255, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    started_at = models.DateTimeField(null=True, blank=True)
    completed_at = models.DateTimeField(null=True, blank=True)
    expires_at = models.DateTimeField()

    class Meta:
        ordering = ["-created_at"]
        indexes = [
            models.Index(
                fields=["requested_by", "status", "-created_at"], name="audit_export_owner_idx"
            ),
            models.Index(fields=["status", "expires_at"], name="audit_export_expiry_idx"),
        ]
        constraints = [
            models.CheckConstraint(
                condition=models.Q(requested_count__gte=1, requested_count__lte=10000),
                name="audit_export_requested_count_bounds",
            )
        ]
