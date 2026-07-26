from django.conf import settings
from django.core.exceptions import ValidationError
from django.db import models
from django.db.models import Q


class Notification(models.Model):
    class Category(models.TextChoices):
        SECURITY = "security", "Security"
        PROJECT = "project", "Project"
        DELIVERABLE = "deliverable", "Deliverable"
        REPORT = "report", "Report"
        DECISION = "decision", "Decision"
        RISK = "risk", "Risk"
        SCHEDULE = "schedule", "Schedule"
        ADMINISTRATION = "administration", "Administration"

    class RequirementType(models.TextChoices):
        INFORMATIONAL = "informational", "Informational"
        ACKNOWLEDGEMENT = "acknowledgement", "Acknowledgement"
        ACTION = "action", "Action"

    class OutcomeState(models.TextChoices):
        NOT_REQUIRED = "not_required", "Not required"
        PENDING = "pending", "Pending"
        ACKNOWLEDGED = "acknowledged", "Acknowledged"
        COMPLETED = "completed", "Completed"
        EXPIRED = "expired", "Expired"
        UNAVAILABLE = "unavailable", "Unavailable"

    class EventType(models.TextChoices):
        VERIFICATION_CODE = "verification_code", "Verification code"
        PASSWORD_RECOVERY = "password_recovery", "Password recovery"
        EMAIL_CHANGE_SECURITY = "email_change_security", "Email change security"
        ROLE_ACTIVATION = "role_activation", "Role activation"
        NEW_SUBMISSION = "new_submission", "New submission"
        PENDING_REVIEW = "pending_review", "Pending review"
        APPROACHING_DEADLINE = "approaching_deadline", "Approaching deadline"
        BOOKING_CHANGED = "booking_changed", "Booking changed"
        TEACHER_FEEDBACK = "teacher_feedback", "Teacher feedback"
        TEACHER_FEEDBACK_AVAILABLE = (
            "teacher_feedback_available",
            "Teacher feedback available",
        )
        MEMBERSHIP_CHANGED = "membership_changed", "Membership changed"
        RESOURCE_USE_DECISION = "resource_use_decision", "Resource use decision"
        SCHEDULE_PUBLISHED = "schedule_published", "Schedule published"
        SCHEDULE_CHANGED = "schedule_changed", "Schedule changed"
        SCHEDULE_CANCELLED = "schedule_cancelled", "Schedule cancelled"
        SCHEDULE_RECIPIENT_REMOVED = (
            "schedule_recipient_removed",
            "Schedule recipient removed",
        )
        SCHEDULE_REMINDER = "schedule_reminder", "Schedule reminder"

    class DeliveryPolicy(models.TextChoices):
        IN_APP = "in_app", "In app"
        IN_APP_EMAIL = "in_app_email", "In app and email"
        EMAIL_ONLY = "email_only", "Email only"

    class Status(models.TextChoices):
        PENDING = "pending", "Pending"
        QUEUED = "queued", "Queued"
        SENT = "sent", "Sent"
        FAILED = "failed", "Failed"
        RETRY_NEEDED = "retry_needed", "Retry needed"
        SKIPPED = "skipped", "Skipped"
        IN_APP_ONLY = "in_app_only", "In app only"

    project = models.ForeignKey(
        "projects.ResearchProject",
        on_delete=models.CASCADE,
        related_name="notifications",
        null=True,
        blank=True,
    )
    recipient = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    recipient_email = models.EmailField(blank=True, db_index=True)
    sender = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="sent_notifications",
    )
    event_type = models.CharField(max_length=40, choices=EventType.choices)
    target_type = models.CharField(max_length=80)
    target_id = models.CharField(max_length=80)
    subject = models.CharField(max_length=255)
    action_path = models.CharField(max_length=512, blank=True)
    status = models.CharField(max_length=20, choices=Status.choices, default=Status.PENDING)
    delivery_policy = models.CharField(
        max_length=20,
        choices=DeliveryPolicy.choices,
        default=DeliveryPolicy.IN_APP_EMAIL,
    )
    eligible_at = models.DateTimeField()
    queued_at = models.DateTimeField(null=True, blank=True)
    sent_at = models.DateTimeField(null=True, blank=True)
    last_attempt_at = models.DateTimeField(null=True, blank=True)
    retry_count = models.PositiveIntegerField(default=0)
    failure_reason = models.TextField(blank=True)
    category = models.CharField(
        max_length=20,
        choices=Category.choices,
        default=Category.ADMINISTRATION,
        db_index=True,
    )
    requirement_type = models.CharField(
        max_length=20,
        choices=RequirementType.choices,
        default=RequirementType.INFORMATIONAL,
    )
    outcome_state = models.CharField(
        max_length=20,
        choices=OutcomeState.choices,
        default=OutcomeState.NOT_REQUIRED,
        db_index=True,
    )
    due_at = models.DateTimeField(null=True, blank=True)
    expires_at = models.DateTimeField(null=True, blank=True)
    acknowledged_at = models.DateTimeField(null=True, blank=True)
    action_completed_at = models.DateTimeField(null=True, blank=True)
    expired_at = models.DateTimeField(null=True, blank=True)
    unavailable_at = models.DateTimeField(null=True, blank=True)
    completion_event_type = models.CharField(max_length=80, blank=True)
    completion_event_id = models.CharField(max_length=80, blank=True)
    dedupe_key = models.CharField(max_length=160, blank=True)
    active_follow_up = models.BooleanField(default=False)
    reminder_count = models.PositiveSmallIntegerField(default=0)
    escalation_level = models.PositiveSmallIntegerField(default=0)
    last_reminded_at = models.DateTimeField(null=True, blank=True)
    last_escalated_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]
        indexes = [
            models.Index(
                fields=["project", "event_type", "target_id"], name="notificatio_project_3dcf0a_idx"
            ),
            models.Index(fields=["recipient", "status"], name="notificatio_recipie_9b7c1f_idx"),
            models.Index(fields=["status", "eligible_at"], name="notificatio_status_44aaf4_idx"),
            models.Index(
                fields=["recipient", "outcome_state", "-created_at"],
                name="notif_outcome_cursor_idx",
            ),
            models.Index(
                fields=["active_follow_up", "due_at"], name="notif_followup_due_idx"
            ),
        ]
        constraints = [
            models.UniqueConstraint(
                fields=["recipient", "dedupe_key"],
                condition=Q(active_follow_up=True) & ~Q(dedupe_key=""),
                name="unique_active_notification_followup",
            ),
            models.CheckConstraint(
                condition=(
                    Q(
                        requirement_type="informational",
                        outcome_state="not_required",
                        active_follow_up=False,
                    )
                    | (
                        ~Q(requirement_type="informational")
                        & ~Q(outcome_state="not_required")
                    )
                ),
                name="notification_requirement_outcome_valid",
            ),
        ]

    def clean(self):
        super().clean()
        if (
            self.requirement_type == self.RequirementType.INFORMATIONAL
            and self.outcome_state != self.OutcomeState.NOT_REQUIRED
        ):
            raise ValidationError("Informational notifications cannot require an outcome.")
        if (
            self.requirement_type != self.RequirementType.INFORMATIONAL
            and self.outcome_state == self.OutcomeState.NOT_REQUIRED
        ):
            raise ValidationError("Actionable notifications require an outcome state.")


class NotificationReadReceipt(models.Model):
    notification = models.ForeignKey(
        Notification,
        on_delete=models.CASCADE,
        related_name="read_receipts",
    )
    viewer = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="notification_read_receipts",
    )
    viewed_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["notification", "viewer"],
                name="unique_notification_viewer_receipt",
            )
        ]
        indexes = [
            models.Index(fields=["viewer", "viewed_at"], name="notificatio_viewer_10c532_idx")
        ]


class NotificationDeliveryAttempt(models.Model):
    class Channel(models.TextChoices):
        IN_APP = "in_app", "In app"
        EMAIL = "email", "Email"

    class State(models.TextChoices):
        PENDING = "pending", "Pending"
        QUEUED = "queued", "Queued"
        SENT = "sent", "Sent"
        FAILED = "failed", "Failed"
        SKIPPED = "skipped", "Skipped"

    notification = models.ForeignKey(
        Notification, on_delete=models.CASCADE, related_name="delivery_attempts"
    )
    channel = models.CharField(max_length=20, choices=Channel.choices)
    attempt_number = models.PositiveSmallIntegerField(default=1)
    state = models.CharField(max_length=20, choices=State.choices, default=State.PENDING)
    eligible_at = models.DateTimeField()
    attempted_at = models.DateTimeField(null=True, blank=True)
    completed_at = models.DateTimeField(null=True, blank=True)
    failure_code = models.CharField(max_length=80, blank=True)
    failure_reason_masked = models.CharField(max_length=500, blank=True)
    idempotency_key = models.CharField(max_length=160, unique=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["notification_id", "channel", "attempt_number"]
        constraints = [
            models.UniqueConstraint(
                fields=["notification", "channel", "attempt_number"],
                name="unique_notification_channel_attempt",
            )
        ]
        indexes = [
            models.Index(fields=["state", "eligible_at"], name="notif_attempt_due_idx")
        ]


class NotificationPreferenceProfile(models.Model):
    user = models.OneToOneField(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="notification_preference_profile",
    )
    quiet_hours_enabled = models.BooleanField(default=False)
    quiet_hours_start = models.TimeField(null=True, blank=True)
    quiet_hours_end = models.TimeField(null=True, blank=True)
    timezone_name = models.CharField(max_length=64, default="UTC")
    version = models.PositiveIntegerField(default=1)
    updated_at = models.DateTimeField(auto_now=True)

    def clean(self):
        super().clean()
        if self.quiet_hours_enabled and (
            self.quiet_hours_start is None or self.quiet_hours_end is None
        ):
            raise ValidationError("Quiet-hour start and end are required.")


class NotificationCategoryPreference(models.Model):
    profile = models.ForeignKey(
        NotificationPreferenceProfile,
        on_delete=models.CASCADE,
        related_name="category_preferences",
    )
    category = models.CharField(max_length=20, choices=Notification.Category.choices)
    email_enabled = models.BooleanField(default=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["profile", "category"],
                name="unique_notification_category_preference",
            )
        ]


class ProjectNotificationPolicy(models.Model):
    project = models.OneToOneField(
        "projects.ResearchProject",
        on_delete=models.CASCADE,
        related_name="notification_policy",
    )
    reminder_lead_minutes = models.PositiveIntegerField(default=1440)
    escalation_delay_minutes = models.PositiveIntegerField(default=1440)
    repeat_interval_minutes = models.PositiveIntegerField(default=1440)
    max_reminders = models.PositiveSmallIntegerField(default=3)
    version = models.PositiveIntegerField(default=1)
    updated_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name="updated_project_notification_policies",
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
