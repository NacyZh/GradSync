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


class WritingProject(models.Model):
    class WritingType(models.TextChoices):
        THESIS = "thesis", "Thesis"
        MANUSCRIPT = "manuscript", "Manuscript"
        PAPER = "paper", "Paper"
        OTHER = "other", "Other"

    class Status(models.TextChoices):
        ACTIVE = "active", "Active"
        CLOSED = "closed", "Closed"
        ARCHIVED = "archived", "Archived"

    project = models.ForeignKey(
        "projects.ResearchProject", on_delete=models.CASCADE, related_name="writing_projects"
    )
    student = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.PROTECT, related_name="writing_projects"
    )
    title = models.CharField(max_length=255)
    writing_type = models.CharField(max_length=30, choices=WritingType.choices)
    status = models.CharField(max_length=20, choices=Status.choices, default=Status.ACTIVE)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["title", "-created_at"]
        indexes = [
            models.Index(fields=["project", "student", "status"], name="sub_writing_scope_idx"),
            models.Index(fields=["project", "title"], name="sub_writing_title_idx"),
        ]

    def __str__(self) -> str:
        return self.title


class WritingVersion(models.Model):
    class FileKind(models.TextChoices):
        WORD = "word", "Word document"
        LATEX_SOURCE = "latex_source", "LaTeX source"
        LATEX_ARCHIVE = "latex_archive", "LaTeX archive"

    class Status(models.TextChoices):
        SUBMITTED = "submitted", "Submitted"
        UNDER_REVIEW = "under_review", "Under review"
        FEEDBACK_AVAILABLE = "feedback_available", "Feedback available"
        CLOSED = "closed", "Closed"

    writing_project = models.ForeignKey(
        WritingProject, on_delete=models.CASCADE, related_name="versions"
    )
    version_number = models.PositiveIntegerField()
    submitted_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.PROTECT, related_name="writing_versions"
    )
    draft_file = models.ForeignKey(
        "common.UploadedFile",
        on_delete=models.PROTECT,
        related_name="writing_versions",
    )
    file_kind = models.CharField(max_length=30, choices=FileKind.choices)
    summary = models.TextField(blank=True)
    status = models.CharField(max_length=30, choices=Status.choices, default=Status.SUBMITTED)
    submitted_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-version_number"]
        unique_together = [("writing_project", "version_number")]
        indexes = [
            models.Index(
                fields=["writing_project", "version_number"], name="sub_writing_version_idx"
            ),
            models.Index(fields=["status", "submitted_at"], name="sub_writing_status_idx"),
        ]


class TeacherFeedback(models.Model):
    class Status(models.TextChoices):
        DRAFT = "draft", "Draft"
        SUBMITTED = "submitted", "Submitted"
        NOTIFICATION_PENDING = "notification_pending", "Notification pending"
        NOTIFICATION_SENT = "notification_sent", "Notification sent"
        NOTIFICATION_FAILED = "notification_failed", "Notification failed"

    writing_version = models.ForeignKey(
        WritingVersion, on_delete=models.CASCADE, related_name="feedback"
    )
    reviewer = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.PROTECT, related_name="teacher_feedback"
    )
    comments = models.TextField(blank=True)
    annotated_file = models.ForeignKey(
        "common.UploadedFile",
        on_delete=models.PROTECT,
        related_name="teacher_feedback",
    )
    notification = models.ForeignKey(
        "notifications.Notification",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="teacher_feedback",
    )
    status = models.CharField(
        max_length=30, choices=Status.choices, default=Status.NOTIFICATION_PENDING
    )
    submitted_at = models.DateTimeField(auto_now_add=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-submitted_at"]
        indexes = [
            models.Index(
                fields=["writing_version", "submitted_at"], name="sub_feedback_version_idx"
            ),
            models.Index(fields=["reviewer", "submitted_at"], name="sub_feedback_reviewer_idx"),
        ]
