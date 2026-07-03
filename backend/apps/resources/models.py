from django.conf import settings
from django.core.exceptions import ValidationError
from django.db import models


class ResourceType(models.Model):
    class Scope(models.TextChoices):
        GLOBAL = "global", "Global"
        PROJECT = "project", "Project"

    class Status(models.TextChoices):
        ACTIVE = "active", "Active"
        ARCHIVED = "archived", "Archived"

    SUPPORTED_FIELD_TYPES = {"text", "number", "boolean", "select", "multi_select", "date"}

    name = models.CharField(max_length=255)
    description = models.TextField(blank=True)
    scope = models.CharField(max_length=20, choices=Scope.choices, default=Scope.GLOBAL)
    field_schema = models.JSONField(default=list, blank=True)
    eligibility_policy = models.JSONField(default=dict, blank=True)
    booking_policy = models.JSONField(default=dict, blank=True)
    status = models.CharField(max_length=20, choices=Status.choices, default=Status.ACTIVE)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["name"]

    def clean(self):
        seen_keys = set()
        for field in self.field_schema or []:
            key = field.get("key")
            field_type = field.get("fieldType") or field.get("field_type")
            if not key:
                raise ValidationError("Resource field keys are required")
            if key in seen_keys:
                raise ValidationError(f"Duplicate resource field key: {key}")
            if field_type not in self.SUPPORTED_FIELD_TYPES:
                raise ValidationError(f"Unsupported resource field type: {field_type}")
            seen_keys.add(key)


class ResourceItem(models.Model):
    class Status(models.TextChoices):
        AVAILABLE = "available", "Available"
        UNAVAILABLE = "unavailable", "Unavailable"
        RETIRED = "retired", "Retired"

    resource_type = models.ForeignKey(
        ResourceType, on_delete=models.PROTECT, related_name="items"
    )
    name = models.CharField(max_length=255)
    description = models.TextField(blank=True)
    location = models.CharField(max_length=255, blank=True)
    field_values = models.JSONField(default=dict, blank=True)
    availability_policy = models.JSONField(default=dict, blank=True)
    status = models.CharField(max_length=20, choices=Status.choices, default=Status.AVAILABLE)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["name"]

    def clean(self):
        schema = self.resource_type.field_schema or []
        values = self.field_values or {}
        schema_by_key = {field.get("key"): field for field in schema if field.get("key")}
        for key, field in schema_by_key.items():
            if field.get("required") and key not in values:
                raise ValidationError(f"Resource field '{key}' is required")
        unsupported = set(values) - set(schema_by_key)
        if unsupported:
            raise ValidationError(f"Unsupported resource field values: {', '.join(sorted(unsupported))}")

class Booking(models.Model):
    class Status(models.TextChoices):
        RESERVED = "reserved", "Reserved"
        CANCELLED = "cancelled", "Cancelled"
        COMPLETED = "completed", "Completed"

    project = models.ForeignKey(
        "projects.ResearchProject", on_delete=models.CASCADE, related_name="bookings"
    )
    resource_item = models.ForeignKey(
        ResourceItem, on_delete=models.PROTECT, related_name="bookings"
    )
    requested_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT)
    starts_at = models.DateTimeField()
    ends_at = models.DateTimeField()
    status = models.CharField(max_length=20, choices=Status.choices, default=Status.RESERVED)
    purpose = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    cancelled_at = models.DateTimeField(null=True, blank=True)
