from rest_framework import serializers

from .models import Notification


class NotificationSerializer(serializers.ModelSerializer):
    class Meta:
        model = Notification
        fields = [
            "id",
            "project_id",
            "recipient_id",
            "sender_id",
            "event_type",
            "target_type",
            "target_id",
            "subject",
            "action_path",
            "status",
            "eligible_at",
            "queued_at",
            "sent_at",
            "failure_reason",
        ]
