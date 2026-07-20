from django.conf import settings
from django.db import models


class Notification(models.Model):
    class EventType(models.TextChoices):
        VERIFICATION_CODE = "verification_code", "Verification code"
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
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]
        indexes = [
            models.Index(
                fields=["project", "event_type", "target_id"], name="notificatio_project_3dcf0a_idx"
            ),
            models.Index(fields=["recipient", "status"], name="notificatio_recipie_9b7c1f_idx"),
            models.Index(fields=["status", "eligible_at"], name="notificatio_status_44aaf4_idx"),
        ]
