from django.conf import settings
from django.db import models


class LabResource(models.Model):
    class ResourceType(models.TextChoices):
        EQUIPMENT = "equipment", "Equipment"
        SEAT = "seat", "Seat"

    class Status(models.TextChoices):
        AVAILABLE = "available", "Available"
        UNAVAILABLE = "unavailable", "Unavailable"
        RETIRED = "retired", "Retired"

    name = models.CharField(max_length=255)
    resource_type = models.CharField(max_length=20, choices=ResourceType.choices)
    location = models.CharField(max_length=255, blank=True)
    status = models.CharField(max_length=20, choices=Status.choices, default=Status.AVAILABLE)
    booking_policy = models.JSONField(default=dict, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)


class Booking(models.Model):
    class Status(models.TextChoices):
        RESERVED = "reserved", "Reserved"
        CANCELLED = "cancelled", "Cancelled"
        COMPLETED = "completed", "Completed"

    project = models.ForeignKey(
        "projects.ResearchProject", on_delete=models.CASCADE, related_name="bookings"
    )
    resource = models.ForeignKey(LabResource, on_delete=models.PROTECT, related_name="bookings")
    requested_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT)
    starts_at = models.DateTimeField()
    ends_at = models.DateTimeField()
    status = models.CharField(max_length=20, choices=Status.choices, default=Status.RESERVED)
    purpose = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    cancelled_at = models.DateTimeField(null=True, blank=True)
