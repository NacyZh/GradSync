from datetime import timedelta
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

from django.conf import settings
from django.core.exceptions import ValidationError
from django.db import models
from django.db.models import Q


class ScheduleItem(models.Model):
    class Scope(models.TextChoices):
        PERSONAL = "personal", "Personal"
        GROUP = "group", "Group"

    class Category(models.TextChoices):
        PERSONAL = "personal", "Personal"
        MEETING = "meeting", "Meeting"
        SEMINAR = "seminar", "Seminar"
        MILESTONE = "milestone", "Milestone"
        DEFENSE = "defense", "Defense"
        DEADLINE = "deadline", "Deadline"
        OTHER = "other", "Other"

    class RecurrenceFrequency(models.TextChoices):
        NONE = "none", "None"
        DAILY = "daily", "Daily"
        WEEKLY = "weekly", "Weekly"
        MONTHLY = "monthly", "Monthly"

    class Status(models.TextChoices):
        ACTIVE = "active", "Active"
        COMPLETED = "completed", "Completed"
        CANCELLED = "cancelled", "Cancelled"

    owner = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="owned_schedule_items"
    )
    organizer = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.PROTECT, related_name="organized_schedule_items"
    )
    scope = models.CharField(max_length=16, choices=Scope.choices, default=Scope.PERSONAL)
    category = models.CharField(max_length=20, choices=Category.choices, default=Category.PERSONAL)
    title = models.CharField(max_length=255)
    description = models.TextField(blank=True, max_length=4000)
    all_day = models.BooleanField(default=False)
    starts_at = models.DateTimeField(null=True, blank=True)
    ends_at = models.DateTimeField(null=True, blank=True)
    starts_on = models.DateField(null=True, blank=True)
    ends_on = models.DateField(null=True, blank=True)
    timezone = models.CharField(max_length=64, default="UTC")
    recurrence_frequency = models.CharField(
        max_length=12,
        choices=RecurrenceFrequency.choices,
        default=RecurrenceFrequency.NONE,
    )
    recurrence_interval = models.PositiveSmallIntegerField(default=1)
    recurrence_weekdays = models.JSONField(default=list, blank=True)
    recurrence_until = models.DateField(null=True, blank=True)
    status = models.CharField(max_length=16, choices=Status.choices, default=Status.ACTIVE)
    published_at = models.DateTimeField(null=True, blank=True)
    cancelled_at = models.DateTimeField(null=True, blank=True)
    version = models.PositiveIntegerField(default=1)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        indexes = [
            models.Index(
                fields=["owner", "scope", "status", "starts_at"], name="sched_owner_timed_idx"
            ),
            models.Index(
                fields=["owner", "scope", "status", "starts_on"], name="sched_owner_day_idx"
            ),
            models.Index(fields=["scope", "status", "published_at"], name="sched_group_state_idx"),
            models.Index(
                fields=["recurrence_frequency", "recurrence_until"], name="sched_recur_until_idx"
            ),
            models.Index(fields=["updated_at", "id"], name="sched_event_cursor_idx"),
        ]

    def clean(self):
        errors = {}
        self.title = self.title.strip()
        if not self.title:
            errors["title"] = "Title is required."
        try:
            ZoneInfo(self.timezone)
        except ZoneInfoNotFoundError:
            errors["timezone"] = "Enter a valid IANA timezone."
        if self.all_day:
            if self.starts_at or self.ends_at or not self.starts_on or not self.ends_on:
                errors["all_day"] = "All-day items require only a date range."
            elif self.ends_on <= self.starts_on:
                errors["ends_on"] = "End date must be after start date."
            first_local_date = self.starts_on
        else:
            if self.starts_on or self.ends_on or not self.starts_at or not self.ends_at:
                errors["all_day"] = "Timed items require only a timestamp range."
            elif self.ends_at <= self.starts_at:
                errors["ends_at"] = "End time must be after start time."
            first_local_date = (
                self.starts_at.astimezone(ZoneInfo(self.timezone)).date()
                if self.starts_at and "timezone" not in errors
                else None
            )
        if not 1 <= self.recurrence_interval <= 30:
            errors["recurrence_interval"] = "Recurrence interval must be between 1 and 30."
        weekdays = self.recurrence_weekdays or []
        if len(weekdays) != len(set(weekdays)) or any(day not in range(1, 8) for day in weekdays):
            errors["recurrence_weekdays"] = "Weekdays must be unique ISO weekdays."
        if self.recurrence_frequency == self.RecurrenceFrequency.NONE:
            if self.recurrence_until or weekdays:
                errors["recurrence_until"] = "Non-recurring items cannot have recurrence bounds."
        else:
            if not self.recurrence_until:
                errors["recurrence_until"] = "Recurring items require an end date."
            elif first_local_date and self.recurrence_until > first_local_date + timedelta(
                days=731
            ):
                errors["recurrence_until"] = "Recurrence cannot span more than two years."
            if self.recurrence_frequency != self.RecurrenceFrequency.WEEKLY and weekdays:
                errors["recurrence_weekdays"] = "Weekdays apply only to weekly recurrence."
        if self.scope == self.Scope.PERSONAL and self.owner_id != self.organizer_id:
            errors["organizer"] = "Personal item organizer must be its owner."
        if self.scope == self.Scope.GROUP and not self.published_at:
            errors["published_at"] = "Published group items require a publication time."
        if errors:
            raise ValidationError(errors)

    def save(self, *args, **kwargs):
        self.full_clean()
        return super().save(*args, **kwargs)


class ScheduleAudience(models.Model):
    class ScopeType(models.TextChoices):
        PROJECT = "project", "Project"
        ACCOUNT = "account", "Account"

    schedule_item = models.ForeignKey(
        ScheduleItem, on_delete=models.CASCADE, related_name="audiences"
    )
    scope_type = models.CharField(max_length=12, choices=ScopeType.choices)
    project = models.ForeignKey(
        "projects.ResearchProject", on_delete=models.CASCADE, null=True, blank=True
    )
    account = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE, null=True, blank=True
    )
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name="created_schedule_audiences",
    )
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["schedule_item", "project"],
                condition=Q(project__isnull=False),
                name="unique_schedule_project_audience",
            ),
            models.UniqueConstraint(
                fields=["schedule_item", "account"],
                condition=Q(account__isnull=False),
                name="unique_schedule_account_audience",
            ),
        ]
        indexes = [
            models.Index(fields=["schedule_item", "scope_type"], name="sched_audience_scope_idx")
        ]

    def clean(self):
        project_shape = (
            self.scope_type == self.ScopeType.PROJECT and self.project_id and not self.account_id
        )
        account_shape = (
            self.scope_type == self.ScopeType.ACCOUNT and self.account_id and not self.project_id
        )
        if not (project_shape or account_shape):
            raise ValidationError("Audience must select exactly one matching project or account.")
        if self.schedule_item_id and self.schedule_item.scope != ScheduleItem.Scope.GROUP:
            raise ValidationError("Audiences apply only to group schedule items.")


class ScheduleRecipientGrant(models.Model):
    schedule_item = models.ForeignKey(
        ScheduleItem, on_delete=models.CASCADE, related_name="recipient_grants"
    )
    recipient = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="schedule_grants"
    )
    valid_from = models.DateTimeField()
    valid_until = models.DateTimeField(null=True, blank=True)
    source_types = models.JSONField(default=list)
    source_project_ids = models.JSONField(default=list, blank=True)
    resolved_at = models.DateTimeField(auto_now=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["schedule_item", "recipient"],
                condition=Q(valid_until__isnull=True),
                name="unique_open_schedule_grant",
            )
        ]
        indexes = [
            models.Index(
                fields=["recipient", "schedule_item", "valid_from", "valid_until"],
                name="sched_grant_visible_idx",
            ),
            models.Index(fields=["schedule_item", "valid_until"], name="sched_grant_open_idx"),
        ]

    def clean(self):
        if self.valid_until and self.valid_until <= self.valid_from:
            raise ValidationError({"valid_until": "Grant end must be after its start."})


class ScheduleOccurrenceException(models.Model):
    class Status(models.TextChoices):
        RESCHEDULED = "rescheduled", "Rescheduled"
        COMPLETED = "completed", "Completed"
        CANCELLED = "cancelled", "Cancelled"

    schedule_item = models.ForeignKey(
        ScheduleItem, on_delete=models.CASCADE, related_name="exceptions"
    )
    original_starts_at = models.DateTimeField(null=True, blank=True)
    original_starts_on = models.DateField(null=True, blank=True)
    override_starts_at = models.DateTimeField(null=True, blank=True)
    override_ends_at = models.DateTimeField(null=True, blank=True)
    override_starts_on = models.DateField(null=True, blank=True)
    override_ends_on = models.DateField(null=True, blank=True)
    override_title = models.CharField(max_length=255, null=True, blank=True)
    override_description = models.TextField(max_length=4000, null=True, blank=True)
    status = models.CharField(max_length=16, choices=Status.choices, default=Status.RESCHEDULED)
    version = models.PositiveIntegerField(default=1)
    created_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["schedule_item", "original_starts_at"],
                condition=Q(original_starts_at__isnull=False),
                name="unique_schedule_timed_exception",
            ),
            models.UniqueConstraint(
                fields=["schedule_item", "original_starts_on"],
                condition=Q(original_starts_on__isnull=False),
                name="unique_schedule_day_exception",
            ),
        ]

    def clean(self):
        if bool(self.original_starts_at) == bool(self.original_starts_on):
            raise ValidationError("Exception requires exactly one original occurrence key.")
        if self.override_starts_at and (
            not self.override_ends_at or self.override_ends_at <= self.override_starts_at
        ):
            raise ValidationError({"override_ends_at": "Override end must be after start."})
        if self.override_starts_on and (
            not self.override_ends_on or self.override_ends_on <= self.override_starts_on
        ):
            raise ValidationError({"override_ends_on": "Override end must be after start."})


class ScheduleReminder(models.Model):
    ALLOWED_OFFSETS = (0, 15, 30, 60, 1440, 10080)
    schedule_item = models.ForeignKey(
        ScheduleItem, on_delete=models.CASCADE, related_name="reminders"
    )
    offset_minutes = models.PositiveIntegerField()
    mandatory = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["schedule_item", "offset_minutes"], name="unique_schedule_reminder"
            )
        ]
        indexes = [
            models.Index(fields=["offset_minutes", "schedule_item"], name="sched_reminder_scan_idx")
        ]

    def clean(self):
        if self.offset_minutes not in self.ALLOWED_OFFSETS:
            raise ValidationError({"offset_minutes": "Unsupported reminder offset."})
        if self.schedule_item_id and not self.pk and self.schedule_item.reminders.count() >= 3:
            raise ValidationError("A schedule item supports at most three reminders.")


class ScheduleRevision(models.Model):
    class ChangeType(models.TextChoices):
        PUBLISHED = "published", "Published"
        CHANGED = "content_changed", "Content changed"
        TIME_CHANGED = "time_changed", "Time changed"
        AUDIENCE_CHANGED = "audience_changed", "Audience changed"
        OCCURRENCE_CHANGED = "occurrence_changed", "Occurrence changed"
        CANCELLED = "cancelled", "Cancelled"

    schedule_item = models.ForeignKey(
        ScheduleItem, on_delete=models.CASCADE, related_name="revisions"
    )
    revision_number = models.PositiveIntegerField()
    actor = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT)
    change_type = models.CharField(max_length=24, choices=ChangeType.choices)
    changed_fields = models.JSONField(default=list, blank=True)
    audience_summary = models.JSONField(default=dict, blank=True)
    effective_from = models.CharField(max_length=40, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["schedule_item", "revision_number"], name="unique_schedule_revision"
            )
        ]
        ordering = ["-revision_number"]


class ScheduleNotificationDispatch(models.Model):
    class EventType(models.TextChoices):
        PUBLISHED = "published", "Published"
        CHANGED = "changed", "Changed"
        CANCELLED = "cancelled", "Cancelled"
        REMOVED = "removed", "Removed"
        REMINDER = "reminder", "Reminder"

    class Channel(models.TextChoices):
        IN_APP = "in_app", "In app"
        EMAIL = "email", "Email"

    class Status(models.TextChoices):
        CLAIMED = "claimed", "Claimed"
        CREATED = "created", "Created"
        SKIPPED = "skipped", "Skipped"
        FAILED = "failed", "Failed"

    schedule_item = models.ForeignKey(
        ScheduleItem, on_delete=models.CASCADE, related_name="notification_dispatches"
    )
    recipient = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    occurrence_key = models.CharField(max_length=40)
    event_type = models.CharField(max_length=16, choices=EventType.choices)
    offset_minutes = models.IntegerField(null=True, blank=True)
    offset_key = models.IntegerField(default=-1, editable=False)
    channel = models.CharField(max_length=12, choices=Channel.choices)
    notification = models.ForeignKey(
        "notifications.Notification", on_delete=models.SET_NULL, null=True, blank=True
    )
    status = models.CharField(max_length=12, choices=Status.choices, default=Status.CLAIMED)
    failure_code = models.CharField(max_length=64, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=[
                    "schedule_item",
                    "recipient",
                    "occurrence_key",
                    "event_type",
                    "offset_key",
                    "channel",
                ],
                name="unique_schedule_dispatch",
            )
        ]
        indexes = [models.Index(fields=["status", "created_at"], name="sched_dispatch_retry_idx")]

    def clean(self):
        if self.event_type == self.EventType.REMINDER and self.offset_minutes is None:
            raise ValidationError({"offset_minutes": "Reminder dispatch requires an offset."})
        if self.event_type != self.EventType.REMINDER and self.offset_minutes is not None:
            raise ValidationError({"offset_minutes": "Only reminder dispatches accept an offset."})

    def save(self, *args, **kwargs):
        self.offset_key = self.offset_minutes if self.offset_minutes is not None else -1
        self.full_clean()
        return super().save(*args, **kwargs)
