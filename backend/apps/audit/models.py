from django.conf import settings
from django.db import models


class AuditEvent(models.Model):
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
    summary = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]


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
