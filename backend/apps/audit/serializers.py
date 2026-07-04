from rest_framework import serializers

from apps.notifications.services import mask_notification_failure_reason

from .models import AuditEvent


class AuditEventSerializer(serializers.ModelSerializer):
    actorId = serializers.IntegerField(source="actor_id", read_only=True)
    targetType = serializers.CharField(source="target_type", read_only=True)
    targetId = serializers.CharField(source="target_id", read_only=True)
    eventType = serializers.CharField(source="event_type", read_only=True)
    createdAt = serializers.DateTimeField(source="created_at", read_only=True)
    summary = serializers.SerializerMethodField()

    class Meta:
        model = AuditEvent
        fields = [
            "id",
            "actorId",
            "eventType",
            "targetType",
            "targetId",
            "summary",
            "createdAt",
        ]

    def get_summary(self, obj: AuditEvent) -> str:
        return mask_notification_failure_reason(obj.summary)
