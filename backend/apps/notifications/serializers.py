from rest_framework import serializers

from .models import (
    Notification,
    NotificationPreferenceProfile,
    ProjectNotificationPolicy,
)
from .services import mask_notification_failure_reason


class NotificationSerializer(serializers.ModelSerializer):
    recipientEmail = serializers.EmailField(source="recipient_email", read_only=True)
    eventType = serializers.CharField(source="event_type", read_only=True)
    targetType = serializers.CharField(source="target_type", read_only=True)
    targetId = serializers.CharField(source="target_id", read_only=True)
    relatedObjectType = serializers.CharField(source="target_type", read_only=True)
    relatedObjectId = serializers.CharField(source="target_id", read_only=True)
    actionPath = serializers.CharField(source="action_path", read_only=True)
    eligibleAt = serializers.DateTimeField(source="eligible_at", read_only=True)
    queuedAt = serializers.DateTimeField(source="queued_at", read_only=True)
    sentAt = serializers.DateTimeField(source="sent_at", read_only=True)
    lastAttemptAt = serializers.DateTimeField(source="last_attempt_at", read_only=True)
    failureReason = serializers.SerializerMethodField()
    deliveryPolicy = serializers.CharField(source="delivery_policy", read_only=True)
    readAt = serializers.DateTimeField(source="viewer_read_at", read_only=True, allow_null=True)
    requirementType = serializers.CharField(source="requirement_type", read_only=True)
    outcomeState = serializers.CharField(source="outcome_state", read_only=True)
    dueAt = serializers.DateTimeField(source="due_at", read_only=True, allow_null=True)
    expiresAt = serializers.DateTimeField(source="expires_at", read_only=True, allow_null=True)
    acknowledgedAt = serializers.DateTimeField(
        source="acknowledged_at", read_only=True, allow_null=True
    )
    actionCompletedAt = serializers.DateTimeField(
        source="action_completed_at", read_only=True, allow_null=True
    )
    activeFollowUp = serializers.BooleanField(source="active_follow_up", read_only=True)
    reminderCount = serializers.IntegerField(source="reminder_count", read_only=True)
    escalationLevel = serializers.IntegerField(source="escalation_level", read_only=True)

    class Meta:
        model = Notification
        fields = [
            "id",
            "project_id",
            "recipient_id",
            "recipient_email",
            "recipientEmail",
            "sender_id",
            "event_type",
            "eventType",
            "target_type",
            "targetType",
            "target_id",
            "targetId",
            "relatedObjectType",
            "relatedObjectId",
            "subject",
            "action_path",
            "actionPath",
            "status",
            "delivery_policy",
            "deliveryPolicy",
            "eligible_at",
            "eligibleAt",
            "queued_at",
            "queuedAt",
            "sent_at",
            "sentAt",
            "last_attempt_at",
            "lastAttemptAt",
            "retry_count",
            "failureReason",
            "readAt",
            "category",
            "requirementType",
            "outcomeState",
            "dueAt",
            "expiresAt",
            "acknowledgedAt",
            "actionCompletedAt",
            "activeFollowUp",
            "reminderCount",
            "escalationLevel",
        ]

    def get_failureReason(self, obj):
        return mask_notification_failure_reason(obj.failure_reason)


class NotificationReadSerializer(serializers.Serializer):
    throughId = serializers.IntegerField(min_value=1, required=False)
    notificationIds = serializers.ListField(
        child=serializers.IntegerField(min_value=1),
        min_length=1,
        max_length=100,
        required=False,
    )

    def validate(self, attrs):
        if bool(attrs.get("throughId")) == bool(attrs.get("notificationIds")):
            raise serializers.ValidationError(
                "Provide either throughId or notificationIds."
            )
        if len(attrs.get("notificationIds", [])) != len(
            set(attrs.get("notificationIds", []))
        ):
            raise serializers.ValidationError("Notification IDs must be unique.")
        return attrs


class NotificationPreferenceWriteSerializer(serializers.Serializer):
    expectedVersion = serializers.IntegerField(min_value=1)
    quietHoursEnabled = serializers.BooleanField()
    quietHoursStart = serializers.TimeField(required=False, allow_null=True)
    quietHoursEnd = serializers.TimeField(required=False, allow_null=True)
    timezone = serializers.CharField(max_length=64)
    categoryEmail = serializers.DictField(
        child=serializers.BooleanField(), required=False, default=dict
    )


class NotificationPreferenceSerializer(serializers.ModelSerializer):
    quietHoursEnabled = serializers.BooleanField(source="quiet_hours_enabled")
    quietHoursStart = serializers.TimeField(source="quiet_hours_start", allow_null=True)
    quietHoursEnd = serializers.TimeField(source="quiet_hours_end", allow_null=True)
    timezone = serializers.CharField(source="timezone_name")
    categories = serializers.SerializerMethodField()

    class Meta:
        model = NotificationPreferenceProfile
        fields = [
            "version",
            "quietHoursEnabled",
            "quietHoursStart",
            "quietHoursEnd",
            "timezone",
            "categories",
        ]

    def get_categories(self, obj):
        preferences = {
            preference.category: preference
            for preference in obj.category_preferences.all()
        }
        return [
            {
                "category": category,
                "emailEnabled": (
                    True
                    if category == Notification.Category.SECURITY
                    else preferences.get(category).email_enabled
                ),
                "emailRequired": category == Notification.Category.SECURITY,
                "inAppEnabled": True,
            }
            for category, _ in Notification.Category.choices
        ]


class ProjectNotificationPolicyWriteSerializer(serializers.Serializer):
    expectedVersion = serializers.IntegerField(min_value=0)
    reminderLeadMinutes = serializers.IntegerField(min_value=1, required=False)
    escalationDelayMinutes = serializers.IntegerField(min_value=1, required=False)
    repeatIntervalMinutes = serializers.IntegerField(min_value=1, required=False)
    maxReminders = serializers.IntegerField(min_value=0, required=False)


class ProjectNotificationPolicySerializer(serializers.ModelSerializer):
    reminderLeadMinutes = serializers.IntegerField(source="reminder_lead_minutes")
    escalationDelayMinutes = serializers.IntegerField(source="escalation_delay_minutes")
    repeatIntervalMinutes = serializers.IntegerField(source="repeat_interval_minutes")
    maxReminders = serializers.IntegerField(source="max_reminders")

    class Meta:
        model = ProjectNotificationPolicy
        fields = [
            "version",
            "reminderLeadMinutes",
            "escalationDelayMinutes",
            "repeatIntervalMinutes",
            "maxReminders",
        ]


class NotificationOperationsSummarySerializer(serializers.Serializer):
    notifications = serializers.IntegerField(min_value=0)
    pendingFollowUps = serializers.IntegerField(min_value=0)
    outcomes = serializers.ListField(child=serializers.DictField())
    deliveryAttempts = serializers.ListField(child=serializers.DictField())
