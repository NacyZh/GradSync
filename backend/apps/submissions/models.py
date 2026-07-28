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
    reporting_period = models.ForeignKey(
        "ReportingPeriod",
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        related_name="reports",
    )
    template_version = models.ForeignKey(
        "ReportTemplateVersion",
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        related_name="reports",
    )
    submitted_late = models.BooleanField(default=False)
    idempotency_key = models.CharField(max_length=100, blank=True)
    response_schema_version = models.PositiveIntegerField(default=1)

    class Meta:
        unique_together = [("project", "student", "report_week_start", "revision_number")]
        ordering = ["-report_week_start", "-revision_number"]
        constraints = [
            models.UniqueConstraint(
                fields=["project", "student", "idempotency_key"],
                condition=~models.Q(idempotency_key=""),
                name="unique_structured_report_retry",
            )
        ]
        indexes = [
            models.Index(
                fields=["reporting_period", "student", "-revision_number"],
                name="sub_report_period_student_idx",
            ),
            models.Index(
                fields=["project", "submitted_late", "review_status", "submitted_at"],
                name="sub_report_lateness_state_idx",
            ),
        ]


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
    deliverable_revision = models.ForeignKey(
        "projects.DeliverableRevision",
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
                        & models.Q(deliverable_revision__isnull=True)
                    )
                    | (
                        models.Q(weekly_report__isnull=True)
                        & models.Q(writing_version__isnull=False)
                        & models.Q(draft_version__isnull=True)
                        & models.Q(deliverable_revision__isnull=True)
                    )
                    | (
                        models.Q(weekly_report__isnull=True)
                        & models.Q(writing_version__isnull=True)
                        & models.Q(draft_version__isnull=False)
                        & models.Q(deliverable_revision__isnull=True)
                    )
                    | (
                        models.Q(weekly_report__isnull=True)
                        & models.Q(writing_version__isnull=True)
                        & models.Q(draft_version__isnull=True)
                        & models.Q(deliverable_revision__isnull=False)
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
            models.UniqueConstraint(
                fields=["reviewer_membership", "deliverable_revision"],
                condition=models.Q(
                    status="active", deliverable_revision__isnull=False
                ),
                name="unique_active_deliverable_review_assignment",
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
            models.Index(
                fields=["deliverable_revision", "status"],
                name="sub_review_deliverable_idx",
            ),
        ]


class ReportTemplate(models.Model):
    project = models.OneToOneField(
        "projects.ResearchProject",
        on_delete=models.CASCADE,
        related_name="report_template",
    )
    name = models.CharField(max_length=255)
    active_version = models.ForeignKey(
        "ReportTemplateVersion",
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        related_name="+",
    )
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name="created_report_templates",
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)


class ReportTemplateVersion(models.Model):
    class Status(models.TextChoices):
        DRAFT = "draft", "Draft"
        PUBLISHED = "published", "Published"
        SUPERSEDED = "superseded", "Superseded"

    project = models.ForeignKey(
        "projects.ResearchProject",
        on_delete=models.CASCADE,
        related_name="report_template_versions",
    )
    template = models.ForeignKey(
        ReportTemplate, on_delete=models.CASCADE, related_name="versions"
    )
    version_number = models.PositiveIntegerField()
    status = models.CharField(
        max_length=16, choices=Status.choices, default=Status.DRAFT
    )
    version = models.PositiveIntegerField(default=1)
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name="created_report_template_versions",
    )
    created_at = models.DateTimeField(auto_now_add=True)
    published_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        related_name="published_report_template_versions",
    )
    published_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ["-version_number"]
        constraints = [
            models.UniqueConstraint(
                fields=["template", "version_number"],
                name="unique_report_template_version",
            ),
            models.UniqueConstraint(
                fields=["template"],
                condition=models.Q(status="draft"),
                name="unique_draft_report_template",
            ),
            models.UniqueConstraint(
                fields=["template"],
                condition=models.Q(status="published"),
                name="unique_published_report_template",
            ),
        ]
        indexes = [
            models.Index(
                fields=["project", "status", "version_number"],
                name="sub_template_project_state_idx",
            ),
            models.Index(
                fields=["template", "status"], name="sub_template_version_state_idx"
            ),
        ]


class ReportTemplateField(models.Model):
    class FieldType(models.TextChoices):
        LONG_TEXT = "long_text", "Long text"
        NUMBER = "number", "Number"
        PERCENTAGE = "percentage", "Percentage"
        SINGLE_CHOICE = "single_choice", "Single choice"
        MULTIPLE_CHOICE = "multiple_choice", "Multiple choice"
        EXECUTION_PROGRESS = "execution_progress", "Execution progress"
        RISK_BLOCKER = "risk_blocker", "Risk or blocker"

    template_version = models.ForeignKey(
        ReportTemplateVersion, on_delete=models.CASCADE, related_name="fields"
    )
    key = models.SlugField(max_length=80)
    label_en = models.CharField(max_length=255)
    label_zh = models.CharField(max_length=255)
    help_text_en = models.TextField(blank=True, max_length=1000)
    help_text_zh = models.TextField(blank=True, max_length=1000)
    field_type = models.CharField(max_length=32, choices=FieldType.choices)
    required = models.BooleanField(default=False)
    order = models.PositiveIntegerField()
    unit = models.CharField(max_length=40, blank=True)
    options = models.JSONField(default=list, blank=True)
    min_value = models.DecimalField(
        max_digits=14, decimal_places=4, null=True, blank=True
    )
    max_value = models.DecimalField(
        max_digits=14, decimal_places=4, null=True, blank=True
    )
    analytics_enabled = models.BooleanField(default=False)

    class Meta:
        ordering = ["order", "id"]
        constraints = [
            models.UniqueConstraint(
                fields=["template_version", "key"],
                name="unique_report_template_field_key",
            ),
            models.UniqueConstraint(
                fields=["template_version", "order"],
                name="unique_report_template_field_order",
            ),
        ]
        indexes = [
            models.Index(
                fields=["template_version", "order"],
                name="sub_template_field_order_idx",
            ),
            models.Index(
                fields=["template_version", "analytics_enabled", "field_type"],
                name="sub_template_field_metric_idx",
            ),
        ]


class ReportingPeriod(models.Model):
    class State(models.TextChoices):
        OPEN = "open", "Open"
        CLOSED = "closed", "Closed"

    project = models.ForeignKey(
        "projects.ResearchProject",
        on_delete=models.CASCADE,
        related_name="reporting_periods",
    )
    starts_on = models.DateField()
    ends_on = models.DateField()
    deadline_at = models.DateTimeField()
    template_version = models.ForeignKey(
        ReportTemplateVersion,
        on_delete=models.PROTECT,
        related_name="reporting_periods",
    )
    state = models.CharField(max_length=10, choices=State.choices, default=State.OPEN)
    opened_at = models.DateTimeField(auto_now_add=True)
    closed_at = models.DateTimeField(null=True, blank=True)
    generation_key = models.CharField(max_length=160, unique=True)

    class Meta:
        ordering = ["-starts_on"]
        constraints = [
            models.UniqueConstraint(
                fields=["project", "starts_on"], name="unique_project_reporting_period"
            )
        ]
        indexes = [
            models.Index(
                fields=["project", "starts_on", "state"],
                name="sub_period_project_state_idx",
            ),
            models.Index(
                fields=["state", "deadline_at"], name="sub_period_deadline_idx"
            ),
            models.Index(
                fields=["template_version", "starts_on"],
                name="sub_period_template_idx",
            ),
        ]


class ReportResponse(models.Model):
    class SourceType(models.TextChoices):
        MILESTONE = "milestone", "Milestone"
        DELIVERABLE = "deliverable", "Deliverable"
        RISK = "risk", "Risk"

    project = models.ForeignKey(
        "projects.ResearchProject",
        on_delete=models.CASCADE,
        related_name="report_responses",
    )
    report = models.ForeignKey(
        WeeklyProgressReport, on_delete=models.CASCADE, related_name="responses"
    )
    template_field = models.ForeignKey(
        ReportTemplateField, on_delete=models.PROTECT, related_name="responses"
    )
    value = models.JSONField()
    numeric_value = models.DecimalField(
        max_digits=14, decimal_places=4, null=True, blank=True
    )
    source_type = models.CharField(
        max_length=20, choices=SourceType.choices, blank=True
    )
    source_id = models.CharField(max_length=80, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["report", "template_field"],
                name="unique_report_field_response",
            )
        ]
        indexes = [
            models.Index(
                fields=["project", "template_field", "numeric_value"],
                name="sub_response_metric_idx",
            ),
            models.Index(
                fields=["report", "template_field"], name="sub_response_report_idx"
            ),
            models.Index(
                fields=["source_type", "source_id"], name="sub_response_source_idx"
            ),
        ]
