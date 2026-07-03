from django.conf import settings
from django.db import models


class Notification(models.Model):
    class EventType(models.TextChoices):
        NEW_SUBMISSION = "new_submission", "New submission"
        PENDING_REVIEW = "pending_review", "Pending review"
        APPROACHING_DEADLINE = "approaching_deadline", "Approaching deadline"
        BOOKING_CHANGED = "booking_changed", "Booking changed"
        TEACHER_FEEDBACK = "teacher_feedback", "Teacher feedback"
        MEMBERSHIP_CHANGED = "membership_changed", "Membership changed"

    class Status(models.TextChoices):
        PENDING = "pending", "Pending"
        QUEUED = "queued", "Queued"
        SENT = "sent", "Sent"
        FAILED = "failed", "Failed"
        SKIPPED = "skipped", "Skipped"

    project = models.ForeignKey(
        "projects.ResearchProject", on_delete=models.CASCADE, related_name="notifications"
    )
    recipient = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
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
    eligible_at = models.DateTimeField()
    queued_at = models.DateTimeField(null=True, blank=True)
    sent_at = models.DateTimeField(null=True, blank=True)
    failure_reason = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]
        indexes = [
            models.Index(
                fields=["project", "event_type", "target_id"], name="notificatio_project_3dcf0a_idx"
            )
        ]
