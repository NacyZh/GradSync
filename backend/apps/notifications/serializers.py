from rest_framework import serializers

from .models import Notification


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
    failureReason = serializers.CharField(source="failure_reason", read_only=True)
    deliveryPolicy = serializers.CharField(source="delivery_policy", read_only=True)

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
            "failure_reason",
            "failureReason",
        ]
