from django.conf import settings
from django.core.exceptions import ValidationError
from django.db import models


class ResourceType(models.Model):
    class ConfirmationPolicy(models.TextChoices):
        IMMEDIATE = "immediate", "Immediate"
        APPROVAL_REQUIRED = "approval_required", "Approval required"

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
    confirmation_policy = models.CharField(
        max_length=24,
        choices=ConfirmationPolicy.choices,
        default=ConfirmationPolicy.IMMEDIATE,
    )
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
    class Kind(models.TextChoices):
        EQUIPMENT = "equipment", "Equipment"
        CONSUMABLE = "consumable", "Consumable"

    class Status(models.TextChoices):
        AVAILABLE = "available", "Available"
        UNAVAILABLE = "unavailable", "Unavailable"
        RETIRED = "retired", "Retired"

    resource_type = models.ForeignKey(ResourceType, on_delete=models.PROTECT, related_name="items")
    kind = models.CharField(max_length=20, choices=Kind.choices, default=Kind.EQUIPMENT)
    name = models.CharField(max_length=255)
    description = models.TextField(blank=True)
    location = models.CharField(max_length=255, blank=True)
    total_quantity = models.PositiveIntegerField(default=1)
    field_values = models.JSONField(default=dict, blank=True)
    availability_policy = models.JSONField(default=dict, blank=True)
    confirmation_policy_override = models.CharField(
        max_length=24,
        choices=ResourceType.ConfirmationPolicy.choices,
        null=True,
        blank=True,
    )
    manager = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="managed_resources",
    )
    use_instructions = models.TextField(blank=True)
    stock_on_hand = models.PositiveIntegerField(default=0)
    reorder_level = models.PositiveIntegerField(default=0)
    stock_unit = models.CharField(max_length=40, blank=True)
    unit_cost = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    calibration_interval_days = models.PositiveIntegerField(null=True, blank=True)
    next_calibration_at = models.DateField(null=True, blank=True)
    status = models.CharField(max_length=20, choices=Status.choices, default=Status.AVAILABLE)
    version = models.PositiveIntegerField(default=1)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["name"]
        constraints = [
            models.CheckConstraint(
                condition=models.Q(total_quantity__gte=1),
                name="resources_item_quantity_gte_1",
            )
        ]
        indexes = [
            models.Index(fields=["resource_type", "status"], name="resources_r_resourc_9d31f5_idx")
        ]

    @property
    def effective_confirmation_policy(self):
        return self.confirmation_policy_override or self.resource_type.confirmation_policy

    def clean(self):
        if self.total_quantity < 1:
            raise ValidationError({"total_quantity": "Resource quantity must be at least 1"})
        schema = self.resource_type.field_schema or []
        values = self.field_values or {}
        schema_by_key = {field.get("key"): field for field in schema if field.get("key")}
        for key, field in schema_by_key.items():
            if field.get("required") and key not in values:
                raise ValidationError(f"Resource field '{key}' is required")
        unsupported = set(values) - set(schema_by_key)
        if unsupported:
            unsupported_fields = ", ".join(sorted(unsupported))
            raise ValidationError(f"Unsupported resource field values: {unsupported_fields}")
        if self.kind == self.Kind.CONSUMABLE and not self.stock_unit.strip():
            raise ValidationError({"stock_unit": "Consumables require a stock unit"})
        if self.kind == self.Kind.CONSUMABLE and self.calibration_interval_days:
            raise ValidationError("Consumables do not support calibration intervals")


class ResourceUseSubmission(models.Model):
    class SubmissionType(models.TextChoices):
        REQUEST = "request", "Request"
        USE_RECORD = "use_record", "Use record"

    class Status(models.TextChoices):
        PENDING = "pending", "Pending"
        CONFIRMED = "confirmed", "Confirmed"
        REJECTED = "rejected", "Rejected"

    resource_item = models.ForeignKey(
        ResourceItem, on_delete=models.PROTECT, related_name="use_submissions"
    )
    student = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.PROTECT, related_name="resource_use_submissions"
    )
    submission_type = models.CharField(max_length=20, choices=SubmissionType.choices)
    details = models.TextField()
    status = models.CharField(max_length=20, choices=Status.choices, default=Status.PENDING)
    reviewer = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="reviewed_resource_use_submissions",
    )
    decision_note = models.TextField(blank=True)
    submitted_at = models.DateTimeField(auto_now_add=True)
    decided_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ["-submitted_at"]
        indexes = [
            models.Index(fields=["resource_item", "status"]),
            models.Index(fields=["student", "status"]),
        ]


class Booking(models.Model):
    class Origin(models.TextChoices):
        STUDENT_REQUEST = "student_request", "Student request"
        STAFF_DIRECT = "staff_direct", "Staff direct"
        LEGACY_BOOKING = "legacy_booking", "Legacy booking"

    class Status(models.TextChoices):
        PENDING = "pending", "Pending"
        CONFIRMED = "confirmed", "Confirmed"
        RESERVED = "reserved", "Reserved (legacy)"
        REJECTED = "rejected", "Rejected"
        CANCELLED = "cancelled", "Cancelled"
        COMPLETED = "completed", "Completed"

    project = models.ForeignKey(
        "projects.ResearchProject",
        on_delete=models.SET_NULL,
        related_name="bookings",
        null=True,
        blank=True,
    )
    resource_item = models.ForeignKey(
        ResourceItem, on_delete=models.PROTECT, related_name="bookings"
    )
    requested_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT)
    starts_at = models.DateTimeField()
    ends_at = models.DateTimeField()
    quantity = models.PositiveIntegerField(default=1)
    origin = models.CharField(
        max_length=24,
        choices=Origin.choices,
        default=Origin.LEGACY_BOOKING,
    )
    confirmation_policy = models.CharField(
        max_length=24,
        choices=ResourceType.ConfirmationPolicy.choices,
        default=ResourceType.ConfirmationPolicy.IMMEDIATE,
    )
    status = models.CharField(max_length=20, choices=Status.choices, default=Status.CONFIRMED)
    purpose = models.TextField(blank=True)
    reviewer = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="reviewed_resource_bookings",
    )
    decision_note = models.TextField(blank=True)
    decided_at = models.DateTimeField(null=True, blank=True)
    version = models.PositiveIntegerField(default=1)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    cancelled_at = models.DateTimeField(null=True, blank=True)
    completed_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        constraints = [
            models.CheckConstraint(
                condition=models.Q(quantity__gte=1), name="booking_quantity_gte_1"
            ),
            models.CheckConstraint(
                condition=models.Q(ends_at__gt=models.F("starts_at")),
                name="booking_end_after_start",
            ),
        ]
        indexes = [
            models.Index(
                fields=["resource_item", "status", "starts_at", "ends_at"],
                name="booking_overlap_idx",
            ),
            models.Index(fields=["requested_by", "status"], name="booking_requester_idx"),
            models.Index(fields=["status", "created_at"], name="booking_review_queue_idx"),
        ]


class ResourceMaintenanceRecord(models.Model):
    class Kind(models.TextChoices):
        PREVENTIVE = "preventive", "Preventive maintenance"
        CALIBRATION = "calibration", "Calibration"
        REPAIR = "repair", "Repair"
        FAULT = "fault", "Fault"

    class Status(models.TextChoices):
        SCHEDULED = "scheduled", "Scheduled"
        IN_PROGRESS = "in_progress", "In progress"
        COMPLETED = "completed", "Completed"
        CANCELLED = "cancelled", "Cancelled"

    resource_item = models.ForeignKey(
        ResourceItem,
        on_delete=models.PROTECT,
        related_name="maintenance_records",
    )
    kind = models.CharField(max_length=20, choices=Kind.choices)
    status = models.CharField(max_length=20, choices=Status.choices, default=Status.SCHEDULED)
    title = models.CharField(max_length=255)
    details = models.TextField(blank=True)
    provider = models.CharField(max_length=255, blank=True)
    scheduled_at = models.DateTimeField()
    due_at = models.DateTimeField(null=True, blank=True)
    completed_at = models.DateTimeField(null=True, blank=True)
    takes_offline = models.BooleanField(default=True)
    cost = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name="created_resource_maintenance",
    )
    completed_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="completed_resource_maintenance",
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-scheduled_at", "-id"]
        indexes = [
            models.Index(
                fields=["resource_item", "status", "scheduled_at"],
                name="resource_maint_status_idx",
            )
        ]


class ConsumableStockTransaction(models.Model):
    class Kind(models.TextChoices):
        RECEIPT = "receipt", "Receipt"
        ISSUE = "issue", "Issue"
        ADJUSTMENT = "adjustment", "Adjustment"

    resource_item = models.ForeignKey(
        ResourceItem,
        on_delete=models.PROTECT,
        related_name="stock_transactions",
    )
    project = models.ForeignKey(
        "projects.ResearchProject",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="consumable_transactions",
    )
    kind = models.CharField(max_length=20, choices=Kind.choices)
    quantity_delta = models.IntegerField()
    balance_after = models.PositiveIntegerField()
    unit_cost = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    note = models.TextField(blank=True)
    recorded_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name="recorded_consumable_transactions",
    )
    recorded_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-recorded_at", "-id"]
        constraints = [
            models.CheckConstraint(
                condition=~models.Q(quantity_delta=0),
                name="consumable_quantity_delta_nonzero",
            )
        ]
        indexes = [
            models.Index(
                fields=["resource_item", "-recorded_at"],
                name="consumable_resource_time_idx",
            )
        ]
