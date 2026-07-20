from rest_framework import serializers

from .models import ScheduleAudience, ScheduleItem, ScheduleReminder


class ScheduleCapabilitiesSerializer(serializers.Serializer):
    canView = serializers.BooleanField(default=True)
    canEdit = serializers.BooleanField(default=False)
    canDelete = serializers.BooleanField(default=False)
    canPublish = serializers.BooleanField(default=False)
    canCancel = serializers.BooleanField(default=False)
    canViewDeliveryStatus = serializers.BooleanField(default=False)
    isReadOnly = serializers.BooleanField(default=True)


class RecurrenceSerializer(serializers.Serializer):
    frequency = serializers.ChoiceField(choices=ScheduleItem.RecurrenceFrequency.choices)
    interval = serializers.IntegerField(min_value=1, max_value=30)
    weekdays = serializers.ListField(
        child=serializers.IntegerField(min_value=1, max_value=7), required=False
    )
    until = serializers.DateField(required=False, allow_null=True)


class ReminderSerializer(serializers.Serializer):
    offsetMinutes = serializers.ChoiceField(
        source="offset_minutes", choices=ScheduleReminder.ALLOWED_OFFSETS
    )
    mandatory = serializers.BooleanField(required=False, default=False)


class ScheduleFieldsSerializer(serializers.Serializer):
    category = serializers.ChoiceField(choices=ScheduleItem.Category.choices, required=False)
    title = serializers.CharField(min_length=1, max_length=255, required=False)
    description = serializers.CharField(max_length=4000, required=False, allow_blank=True)
    allDay = serializers.BooleanField(source="all_day", required=False)
    startsAt = serializers.DateTimeField(source="starts_at", required=False, allow_null=True)
    endsAt = serializers.DateTimeField(source="ends_at", required=False, allow_null=True)
    startsOn = serializers.DateField(source="starts_on", required=False, allow_null=True)
    endsOn = serializers.DateField(source="ends_on", required=False, allow_null=True)
    timezone = serializers.CharField(max_length=64, required=False)
    recurrence = RecurrenceSerializer(required=False)
    reminders = ReminderSerializer(many=True, required=False)

    def validate_reminders(self, value):
        offsets = [item["offset_minutes"] for item in value]
        if len(offsets) > 3:
            raise serializers.ValidationError("Choose at most three reminders.")
        if len(offsets) != len(set(offsets)):
            raise serializers.ValidationError("Reminder offsets must be unique.")
        return value


class AudienceSelectionSerializer(serializers.Serializer):
    projectIds = serializers.ListField(
        source="project_ids",
        child=serializers.IntegerField(min_value=1),
        max_length=50,
        required=False,
        default=list,
    )
    accountIds = serializers.ListField(
        source="account_ids",
        child=serializers.IntegerField(min_value=1),
        max_length=500,
        required=False,
        default=list,
    )


class ScheduleCreateSerializer(ScheduleFieldsSerializer):
    scope = serializers.ChoiceField(choices=ScheduleItem.Scope.choices)
    audience = AudienceSelectionSerializer(required=False)
    confirmConflicts = serializers.BooleanField(source="confirm_conflicts", default=False)

    def validate(self, attrs):
        if not attrs.get("title", "").strip():
            raise serializers.ValidationError({"title": "Title is required."})
        return attrs


class ScheduleUpdateSerializer(serializers.Serializer):
    expectedVersion = serializers.IntegerField(source="expected_version", min_value=1)
    changeScope = serializers.ChoiceField(
        source="change_scope", choices=["occurrence", "future", "series"]
    )
    occurrenceKey = serializers.CharField(
        source="occurrence_key", required=False, allow_blank=False, allow_null=True
    )
    fields = ScheduleFieldsSerializer(required=False, default=dict)
    audience = AudienceSelectionSerializer(required=False)
    confirmConflicts = serializers.BooleanField(source="confirm_conflicts", default=False)

    def validate(self, attrs):
        if attrs["change_scope"] in {"occurrence", "future"} and not attrs.get("occurrence_key"):
            raise serializers.ValidationError(
                {"occurrenceKey": "This change scope requires an occurrence."}
            )
        return attrs


class ScheduleActionSerializer(serializers.Serializer):
    expectedVersion = serializers.IntegerField(source="expected_version", min_value=1)
    changeScope = serializers.ChoiceField(
        source="change_scope", choices=["occurrence", "future", "series"]
    )
    occurrenceKey = serializers.CharField(source="occurrence_key", required=False, allow_null=True)
    confirmed = serializers.BooleanField()

    def validate(self, attrs):
        if not attrs["confirmed"]:
            raise serializers.ValidationError({"confirmed": "Confirm this operation."})
        if attrs["change_scope"] in {"occurrence", "future"} and not attrs.get("occurrence_key"):
            raise serializers.ValidationError(
                {"occurrenceKey": "This change scope requires an occurrence."}
            )
        return attrs


class ScheduleCancelSerializer(ScheduleActionSerializer):
    reason = serializers.CharField(required=False, allow_blank=True, max_length=500)


class SchedulePublishSerializer(serializers.Serializer):
    expectedVersion = serializers.IntegerField(source="expected_version", min_value=1)
    audience = AudienceSelectionSerializer()
    reminders = ReminderSerializer(many=True, required=False)
    confirmed = serializers.BooleanField()
    confirmConflicts = serializers.BooleanField(source="confirm_conflicts", default=False)

    def validate(self, attrs):
        if not attrs["confirmed"]:
            raise serializers.ValidationError({"confirmed": "Confirm publication."})
        return attrs


class ConflictCheckSerializer(serializers.Serializer):
    scheduleId = serializers.IntegerField(source="schedule_id", required=False, allow_null=True)
    allDay = serializers.BooleanField(source="all_day")
    startsAt = serializers.DateTimeField(source="starts_at", required=False, allow_null=True)
    endsAt = serializers.DateTimeField(source="ends_at", required=False, allow_null=True)
    startsOn = serializers.DateField(source="starts_on", required=False, allow_null=True)
    endsOn = serializers.DateField(source="ends_on", required=False, allow_null=True)
    timezone = serializers.CharField(required=False, default="UTC")

    def validate(self, attrs):
        if attrs["all_day"]:
            if not attrs.get("starts_on") or not attrs.get("ends_on"):
                raise serializers.ValidationError({"startsOn": "Date range is required."})
        elif not attrs.get("starts_at") or not attrs.get("ends_at"):
            raise serializers.ValidationError({"startsAt": "Time range is required."})
        return attrs


class ScheduleOccurrenceSerializer(serializers.Serializer):
    occurrenceId = serializers.CharField()
    sourceType = serializers.ChoiceField(
        choices=["schedule", "project", "task", "report", "booking"]
    )
    sourceId = serializers.CharField()
    scheduleId = serializers.IntegerField(required=False, allow_null=True)
    scope = serializers.ChoiceField(choices=["personal", "group", "system"])
    category = serializers.CharField()
    title = serializers.CharField()
    description = serializers.CharField(required=False, allow_blank=True)
    startsAt = serializers.DateTimeField(required=False, allow_null=True)
    endsAt = serializers.DateTimeField(required=False, allow_null=True)
    startsOn = serializers.DateField(required=False, allow_null=True)
    endsOn = serializers.DateField(required=False, allow_null=True)
    allDay = serializers.BooleanField()
    timezone = serializers.CharField()
    status = serializers.CharField()
    actionPath = serializers.CharField(required=False, allow_blank=True, allow_null=True)
    version = serializers.IntegerField(required=False, allow_null=True)
    capabilities = ScheduleCapabilitiesSerializer()


class ScheduleItemSerializer(serializers.ModelSerializer):
    startsAt = serializers.DateTimeField(source="starts_at", allow_null=True)
    endsAt = serializers.DateTimeField(source="ends_at", allow_null=True)
    startsOn = serializers.DateField(source="starts_on", allow_null=True)
    endsOn = serializers.DateField(source="ends_on", allow_null=True)
    allDay = serializers.BooleanField(source="all_day")
    recurrenceFrequency = serializers.CharField(source="recurrence_frequency")
    recurrenceInterval = serializers.IntegerField(source="recurrence_interval")
    recurrenceWeekdays = serializers.JSONField(source="recurrence_weekdays")
    recurrenceUntil = serializers.DateField(source="recurrence_until", allow_null=True)
    ownerId = serializers.IntegerField(source="owner_id", read_only=True)
    organizerId = serializers.IntegerField(source="organizer_id", read_only=True)

    class Meta:
        model = ScheduleItem
        fields = [
            "id",
            "ownerId",
            "organizerId",
            "scope",
            "category",
            "title",
            "description",
            "allDay",
            "startsAt",
            "endsAt",
            "startsOn",
            "endsOn",
            "timezone",
            "recurrenceFrequency",
            "recurrenceInterval",
            "recurrenceWeekdays",
            "recurrenceUntil",
            "status",
            "version",
        ]

    def validate(self, attrs):
        if self.initial_data.get("audience") == "all":
            raise serializers.ValidationError({"audience": "All-account broadcast is unsupported."})
        return attrs


class ScheduleAudienceSerializer(serializers.ModelSerializer):
    projectId = serializers.IntegerField(source="project_id", allow_null=True)
    accountId = serializers.IntegerField(source="account_id", allow_null=True)

    class Meta:
        model = ScheduleAudience
        fields = ["id", "scope_type", "projectId", "accountId"]


class VersionConflictSerializer(serializers.Serializer):
    code = serializers.CharField(default="version_conflict")
    message = serializers.CharField()
    currentVersion = serializers.IntegerField()
    current = serializers.DictField(required=False)


def schedule_detail(item, user):
    is_owner = item.owner_id == user.id
    can_manage_group = item.scope == ScheduleItem.Scope.GROUP and (
        is_owner or getattr(user, "is_administrator", False)
    )
    return {
        "id": item.id,
        "occurrenceId": f"schedule:{item.id}",
        "sourceType": "schedule",
        "sourceId": str(item.id),
        "scheduleId": item.id,
        "scope": item.scope,
        "category": item.category,
        "title": item.title,
        "description": item.description,
        "allDay": item.all_day,
        "startsAt": item.starts_at,
        "endsAt": item.ends_at,
        "startsOn": item.starts_on,
        "endsOn": item.ends_on,
        "timezone": item.timezone,
        "status": item.status,
        "owner": {"id": item.owner_id, "name": item.owner.name, "role": item.owner.global_role},
        "organizer": {
            "id": item.organizer_id,
            "name": item.organizer.name,
            "role": item.organizer.global_role,
        },
        "recurrence": {
            "frequency": item.recurrence_frequency,
            "interval": item.recurrence_interval,
            "weekdays": item.recurrence_weekdays,
            "until": item.recurrence_until,
        },
        "reminders": [
            {"offsetMinutes": reminder.offset_minutes, "mandatory": reminder.mandatory}
            for reminder in item.reminders.all()
        ],
        "audience": {
            "projectIds": [
                audience.project_id for audience in item.audiences.all() if audience.project_id
            ],
            "accountIds": [
                audience.account_id for audience in item.audiences.all() if audience.account_id
            ],
        },
        "publishedAt": item.published_at,
        "cancelledAt": item.cancelled_at,
        "version": item.version,
        "capabilities": {
            "canView": True,
            "canEdit": is_owner or can_manage_group,
            "canDelete": is_owner and item.scope == ScheduleItem.Scope.PERSONAL,
            "canPublish": is_owner and item.scope == ScheduleItem.Scope.PERSONAL,
            "canCancel": can_manage_group,
            "canViewDeliveryStatus": can_manage_group,
            "isReadOnly": not (is_owner or can_manage_group),
        },
    }
