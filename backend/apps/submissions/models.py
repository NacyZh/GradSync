import uuid
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

from django.conf import settings
from django.core.exceptions import ValidationError
from django.db import models


class ProjectReportSchedule(models.Model):
    project = models.OneToOneField(
        "projects.ResearchProject", on_delete=models.CASCADE, related_name="report_schedule"
    )
    weekday = models.PositiveSmallIntegerField()
    deadline_time = models.TimeField()
    timezone = models.CharField(max_length=64, default="UTC")
    version = models.PositiveIntegerField(default=1)
    updated_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.PROTECT, related_name="updated_report_schedules"
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        indexes = [models.Index(fields=["weekday", "project"], name="sub_report_policy_due_idx")]

    def clean(self):
        errors = {}
        if self.weekday not in range(1, 8):
            errors["weekday"] = "Weekday must be an ISO weekday from 1 to 7."
        try:
            ZoneInfo(self.timezone)
        except ZoneInfoNotFoundError:
            errors["timezone"] = "Enter a valid IANA timezone."
        if self.project_id and self.project.status != "active":
            errors["project"] = "Archived projects cannot configure report deadlines."
        if errors:
            raise ValidationError(errors)

    def save(self, *args, **kwargs):
        self.full_clean()
        return super().save(*args, **kwargs)


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
    revision_number = models.PositiveIntegerField(default=1)
    review_status = models.CharField(
        max_length=30, choices=ReviewStatus.choices, default=ReviewStatus.PENDING_REVIEW
    )
    submitted_at = models.DateTimeField(auto_now_add=True)
    reviewed_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        unique_together = [("project", "student", "report_week_start", "revision_number")]
        ordering = ["-report_week_start", "-revision_number"]


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
    legacy_project = models.ForeignKey(
        "projects.ResearchProject",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="legacy_writing_projects",
    )
    student = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.PROTECT, related_name="writing_projects"
    )
    title = models.CharField(max_length=255)
    writing_type = models.CharField(max_length=30, choices=WritingType.choices)
    status = models.CharField(max_length=20, choices=Status.choices, default=Status.ACTIVE)
    migrated_from_project_nested_area = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["title", "-created_at"]
        indexes = [
            models.Index(fields=["project", "student", "status"], name="sub_writing_scope_idx"),
            models.Index(fields=["project", "title"], name="sub_writing_title_idx"),
            models.Index(fields=["student", "status"], name="sub_writing_student_idx"),
            models.Index(fields=["legacy_project", "status"], name="sub_writing_legacy_idx"),
        ]

    def __str__(self) -> str:
        return self.title


class WritingParticipant(models.Model):
    class Role(models.TextChoices):
        STUDENT_AUTHOR = "student_author", "Student author"
        BOUND_ADVISOR = "bound_advisor", "Bound advisor"
        ASSIGNED_REVIEWER = "assigned_reviewer", "Assigned reviewer"
        ADMINISTRATOR = "administrator", "Administrator"

    class Status(models.TextChoices):
        ACTIVE = "active", "Active"
        REMOVED = "removed", "Removed"

    writing_project = models.ForeignKey(
        WritingProject, on_delete=models.CASCADE, related_name="participants"
    )
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="writing_participations"
    )
    participant_role = models.CharField(max_length=30, choices=Role.choices)
    status = models.CharField(max_length=20, choices=Status.choices, default=Status.ACTIVE)
    assigned_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="assigned_writing_participants",
    )
    assigned_at = models.DateTimeField(auto_now_add=True)
    removed_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        indexes = [
            models.Index(
                fields=["writing_project", "user", "status"],
                name="sub_wpart_project_user_idx",
            ),
            models.Index(fields=["user", "participant_role", "status"], name="sub_wpart_role_idx"),
        ]


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


class SubmissionReviewAssignment(models.Model):
    class Status(models.TextChoices):
        ACTIVE = "active", "Active"
        REMOVED = "removed", "Removed"

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    project = models.ForeignKey(
        "projects.ResearchProject",
        on_delete=models.CASCADE,
        related_name="review_assignments",
    )
    reviewer_membership = models.ForeignKey(
        "projects.ProjectMembership",
        on_delete=models.PROTECT,
        related_name="review_assignments",
    )
    weekly_report = models.ForeignKey(
        WeeklyProgressReport,
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name="review_assignments",
    )
    writing_version = models.ForeignKey(
        WritingVersion,
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name="review_assignments",
    )
    draft_version = models.ForeignKey(
        DraftVersion,
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name="review_assignments",
    )
    status = models.CharField(max_length=20, choices=Status.choices, default=Status.ACTIVE)
    assigned_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name="created_review_assignments",
    )
    assigned_at = models.DateTimeField(auto_now_add=True)
    removed_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        related_name="removed_review_assignments",
    )
    removed_at = models.DateTimeField(null=True, blank=True)
    version = models.PositiveIntegerField(default=1)

    class Meta:
        constraints = [
            models.CheckConstraint(
                condition=(
                    (
                        models.Q(weekly_report__isnull=False)
                        & models.Q(writing_version__isnull=True)
                        & models.Q(draft_version__isnull=True)
                    )
                    | (
                        models.Q(weekly_report__isnull=True)
                        & models.Q(writing_version__isnull=False)
                        & models.Q(draft_version__isnull=True)
                    )
                    | (
                        models.Q(weekly_report__isnull=True)
                        & models.Q(writing_version__isnull=True)
                        & models.Q(draft_version__isnull=False)
                    )
                ),
                name="review_assignment_exactly_one_target",
            ),
            models.UniqueConstraint(
                fields=["reviewer_membership", "weekly_report"],
                condition=models.Q(status="active", weekly_report__isnull=False),
                name="unique_active_weekly_review_assignment",
            ),
            models.UniqueConstraint(
                fields=["reviewer_membership", "writing_version"],
                condition=models.Q(status="active", writing_version__isnull=False),
                name="unique_active_writing_review_assignment",
            ),
            models.UniqueConstraint(
                fields=["reviewer_membership", "draft_version"],
                condition=models.Q(status="active", draft_version__isnull=False),
                name="unique_active_draft_review_assignment",
            ),
        ]
        indexes = [
            models.Index(
                fields=["reviewer_membership", "status", "-assigned_at"],
                name="sub_review_member_idx",
            ),
            models.Index(fields=["weekly_report", "status"], name="sub_review_weekly_idx"),
            models.Index(fields=["writing_version", "status"], name="sub_review_writing_idx"),
            models.Index(fields=["draft_version", "status"], name="sub_review_draft_idx"),
        ]
