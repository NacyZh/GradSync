from rest_framework import serializers

from .models import ProjectMembership, ResearchProject
from .services import ProjectService


class ProjectMembershipSerializer(serializers.ModelSerializer):
    class Meta:
        model = ProjectMembership
        fields = ["id", "project_id", "user_id", "role", "status", "joined_at", "removed_at"]


class ProjectCreateSerializer(serializers.Serializer):
    title = serializers.CharField(max_length=255)
    description = serializers.CharField(required=False, allow_blank=True)
    starts_on = serializers.DateField(required=False, allow_null=True)
    ends_on = serializers.DateField(required=False, allow_null=True)
    student_ids = serializers.ListField(child=serializers.IntegerField(), required=False)

    def validate(self, attrs):
        starts_on = attrs.get("starts_on")
        ends_on = attrs.get("ends_on")
        if starts_on and ends_on and ends_on < starts_on:
            raise serializers.ValidationError("Project end date cannot be before start date")
        return attrs

    def create(self, validated_data):
        return ProjectService(self.context["request"].user).create_project(**validated_data)


class ProjectSerializer(serializers.ModelSerializer):
    memberships = ProjectMembershipSerializer(many=True, read_only=True)

    class Meta:
        model = ResearchProject
        fields = [
            "id",
            "title",
            "description",
            "advisor_id",
            "status",
            "starts_on",
            "ends_on",
            "archived_at",
            "memberships",
        ]


class ProjectUpdateSerializer(serializers.ModelSerializer):
    class Meta:
        model = ResearchProject
        fields = ["title", "description", "starts_on", "ends_on"]
        extra_kwargs = {field: {"required": False} for field in fields}

    def validate(self, attrs):
        starts_on = attrs.get("starts_on", getattr(self.instance, "starts_on", None))
        ends_on = attrs.get("ends_on", getattr(self.instance, "ends_on", None))
        if starts_on and ends_on and ends_on < starts_on:
            raise serializers.ValidationError("Project end date cannot be before start date")
        return attrs


class ProjectDashboardSerializer(ProjectSerializer):
    current_tasks = serializers.SerializerMethodField()
    pending_reviews = serializers.SerializerMethodField()
    upcoming_bookings = serializers.SerializerMethodField()

    class Meta(ProjectSerializer.Meta):
        fields = ProjectSerializer.Meta.fields + [
            "current_tasks",
            "pending_reviews",
            "upcoming_bookings",
        ]

    def get_current_tasks(self, obj):
        from apps.tasks.serializers import TaskSerializer

        tasks = obj.tasks.exclude(status__in=["completed", "cancelled"]).order_by(
            "parent_task_id", "id"
        )[:20]
        return TaskSerializer(
            tasks,
            many=True,
        ).data

    def get_pending_reviews(self, obj):
        pending = []
        for version in obj.draft_versions.filter(review_status="pending_review").order_by(
            "-submitted_at"
        )[:10]:
            pending.append(
                {
                    "target_type": "draft_version",
                    "target_id": str(version.id),
                    "submitted_at": version.submitted_at,
                }
            )
        for report in obj.weekly_reports.filter(review_status="pending_review").order_by(
            "-submitted_at"
        )[:10]:
            pending.append(
                {
                    "target_type": "progress_report",
                    "target_id": str(report.id),
                    "submitted_at": report.submitted_at,
                }
            )
        return sorted(pending, key=lambda item: item["submitted_at"], reverse=True)[:10]

    def get_upcoming_bookings(self, obj):
        from apps.resources.serializers import BookingSerializer

        return BookingSerializer(
            obj.bookings.filter(status="reserved").order_by("starts_at")[:10], many=True
        ).data

    def to_representation(self, instance):
        data = super().to_representation(instance)
        audit_events = [
            {
                "source": "audit",
                "event_type": event.event_type,
                "summary": event.summary,
                "actor_id": event.actor_id,
                "created_at": event.created_at,
            }
            for event in instance.audit_events.select_related("actor")[:20]
        ]
        comment_events = [
            {
                "source": "comment",
                "event_type": "inline_comment." + comment.status,
                "summary": (
                    f"Comment on {comment.target_type} {comment.target_id}: {comment.anchor}"
                ),
                "actor_id": comment.author_id,
                "created_at": comment.created_at,
            }
            for comment in instance.inline_comments.select_related("author")[:20]
        ]
        notification_events = [
            {
                "source": "notification",
                "event_type": "notification." + notification.status,
                "summary": notification.subject,
                "actor_id": notification.sender_id,
                "created_at": notification.created_at,
            }
            for notification in instance.notifications.select_related("sender")[:20]
        ]
        data["activity"] = sorted(
            [*audit_events, *comment_events, *notification_events],
            key=lambda item: item["created_at"],
            reverse=True,
        )[:20]
        return data
