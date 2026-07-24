from django.utils import timezone
from rest_framework import serializers

from apps.notifications.services import mask_notification_failure_reason

from .models import AuditEvent, AuditExport
from .services import redact_snapshot


class AuditEventSerializer(serializers.ModelSerializer):
    actorId = serializers.IntegerField(source="actor_id", read_only=True)
    targetType = serializers.CharField(source="target_type", read_only=True)
    targetId = serializers.CharField(source="target_id", read_only=True)
    eventType = serializers.CharField(source="event_type", read_only=True)
    createdAt = serializers.DateTimeField(source="created_at", read_only=True)
    correlationId = serializers.CharField(source="correlation_id", read_only=True)
    actorSnapshot = serializers.SerializerMethodField()
    targetSnapshot = serializers.SerializerMethodField()
    redactionVersion = serializers.IntegerField(source="redaction_version", read_only=True)
    summary = serializers.SerializerMethodField()

    class Meta:
        model = AuditEvent
        fields = [
            "id",
            "actorId",
            "eventType",
            "category",
            "outcome",
            "reason",
            "correlationId",
            "actorSnapshot",
            "targetType",
            "targetId",
            "targetSnapshot",
            "redactionVersion",
            "summary",
            "createdAt",
        ]

    def get_summary(self, obj: AuditEvent) -> str:
        return mask_notification_failure_reason(obj.summary)

    def get_actorSnapshot(self, obj: AuditEvent):
        return redact_snapshot(
            obj.actor_snapshot,
            allowed_keys={"id", "email", "name", "role"},
        )

    def get_targetSnapshot(self, obj: AuditEvent):
        return redact_snapshot(obj.target_snapshot)


class AuditExportSerializer(serializers.ModelSerializer):
    requestedCount = serializers.IntegerField(source="requested_count", read_only=True)
    exportedCount = serializers.IntegerField(source="exported_count", read_only=True)
    filterSnapshot = serializers.SerializerMethodField()
    failureReason = serializers.CharField(source="failure_reason", read_only=True)
    createdAt = serializers.DateTimeField(source="created_at", read_only=True)
    completedAt = serializers.DateTimeField(source="completed_at", read_only=True)
    expiresAt = serializers.DateTimeField(source="expires_at", read_only=True)
    capabilities = serializers.SerializerMethodField()

    class Meta:
        model = AuditExport
        fields = [
            "id",
            "status",
            "requestedCount",
            "exportedCount",
            "filterSnapshot",
            "failureReason",
            "createdAt",
            "completedAt",
            "expiresAt",
            "capabilities",
        ]

    def get_filterSnapshot(self, obj):
        return redact_snapshot(obj.filter_snapshot, allowed_keys=set(obj.filter_snapshot))

    def get_capabilities(self, obj):
        request = self.context.get("request")
        user = getattr(request, "user", None)
        current_admin = bool(
            user
            and getattr(user, "is_authenticated", False)
            and getattr(user, "is_administrator", False)
        )
        return {
            "canDownload": current_admin
            and obj.requested_by_id == getattr(user, "id", None)
            and obj.status == AuditExport.Status.READY
            and obj.expires_at > timezone.now(),
            "canRetry": current_admin
            and obj.requested_by_id == getattr(user, "id", None)
            and obj.status == AuditExport.Status.FAILED,
        }
