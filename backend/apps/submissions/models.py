from django.conf import settings
from django.db import models


class Draft(models.Model):
    class Status(models.TextChoices):
        ACTIVE = "active", "Active"
        CLOSED = "closed", "Closed"

    project = models.ForeignKey(
        "projects.ResearchProject", on_delete=models.CASCADE, related_name="drafts"
    )
    title = models.CharField(max_length=255)
    student = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.PROTECT, related_name="drafts"
    )
    status = models.CharField(max_length=20, choices=Status.choices, default=Status.ACTIVE)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)


class DraftVersion(models.Model):
    class ReviewStatus(models.TextChoices):
        PENDING_REVIEW = "pending_review", "Pending review"
        REVIEWED = "reviewed", "Reviewed"
        NEEDS_REVISION = "needs_revision", "Needs revision"
        CLOSED = "closed", "Closed"

    draft = models.ForeignKey(Draft, on_delete=models.CASCADE, related_name="versions")
    project = models.ForeignKey(
        "projects.ResearchProject", on_delete=models.CASCADE, related_name="draft_versions"
    )
    version_number = models.PositiveIntegerField()
    submitted_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT)
    content_reference = models.CharField(max_length=512)
    summary = models.TextField(blank=True)
    review_status = models.CharField(
        max_length=30, choices=ReviewStatus.choices, default=ReviewStatus.PENDING_REVIEW
    )
    submitted_at = models.DateTimeField(auto_now_add=True)
    reviewed_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        unique_together = [("draft", "version_number")]
        ordering = ["-version_number"]


class WeeklyProgressReport(models.Model):
    class ReviewStatus(models.TextChoices):
        PENDING_REVIEW = "pending_review", "Pending review"
        REVIEWED = "reviewed", "Reviewed"
        NEEDS_REVISION = "needs_revision", "Needs revision"
        CLOSED = "closed", "Closed"

    project = models.ForeignKey(
        "projects.ResearchProject", on_delete=models.CASCADE, related_name="weekly_reports"
    )
    student = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.PROTECT, related_name="weekly_reports"
    )
    report_week_start = models.DateField()
    completed_work = models.TextField()
    blockers = models.TextField(blank=True)
    next_steps = models.TextField()
    attachment_reference = models.CharField(max_length=512, blank=True)
    review_status = models.CharField(
        max_length=30, choices=ReviewStatus.choices, default=ReviewStatus.PENDING_REVIEW
    )
    submitted_at = models.DateTimeField(auto_now_add=True)
    reviewed_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        unique_together = [("project", "student", "report_week_start")]
        ordering = ["-report_week_start"]


class InlineComment(models.Model):
    class TargetType(models.TextChoices):
        DRAFT_VERSION = "draft_version", "Draft version"
        PROGRESS_REPORT = "progress_report", "Progress report"

    class Status(models.TextChoices):
        OPEN = "open", "Open"
        RESOLVED = "resolved", "Resolved"

    project = models.ForeignKey(
        "projects.ResearchProject", on_delete=models.CASCADE, related_name="inline_comments"
    )
    target_type = models.CharField(max_length=30, choices=TargetType.choices)
    target_id = models.PositiveIntegerField()
    author = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT)
    anchor = models.CharField(max_length=255)
    body = models.TextField()
    status = models.CharField(max_length=20, choices=Status.choices, default=Status.OPEN)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    resolved_at = models.DateTimeField(null=True, blank=True)
