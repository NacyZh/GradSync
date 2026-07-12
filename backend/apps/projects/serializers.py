from drf_spectacular.utils import extend_schema_field
from rest_framework import serializers

from .material_services import (
    project_material_capabilities,
    project_material_display_name,
)
from .models import ProjectMaterial, ProjectMembership, ResearchProject
from .services import ProjectService


class ProjectMembershipSerializer(serializers.ModelSerializer):
    projectId = serializers.IntegerField(source="project_id", read_only=True)
    userId = serializers.IntegerField(source="user_id", read_only=True)
    nickname = serializers.CharField(source="user.nickname", read_only=True)
    name = serializers.CharField(source="user.name", read_only=True)
    email = serializers.EmailField(source="user.email", read_only=True)
    joinedAt = serializers.DateTimeField(source="joined_at", read_only=True)
    removedAt = serializers.DateTimeField(source="removed_at", read_only=True)

    class Meta:
        model = ProjectMembership
        fields = [
            "id",
            "project_id",
            "user_id",
            "projectId",
            "userId",
            "nickname",
            "name",
            "email",
            "role",
            "status",
            "joined_at",
            "removed_at",
            "joinedAt",
            "removedAt",
        ]


class MembershipCreateSerializer(serializers.Serializer):
    studentId = serializers.IntegerField()


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


class ProjectMaterialSerializer(serializers.ModelSerializer):
    materialType = serializers.CharField(source="material_type", read_only=True)
    backingRecordId = serializers.CharField(source="backing_record_id", read_only=True)
    sourceProject = serializers.SerializerMethodField()
    visibility = serializers.CharField(source="visibility_state", read_only=True)
    classificationState = serializers.CharField(source="classification_state", read_only=True)
    displayName = serializers.SerializerMethodField()
    actionCapabilities = serializers.SerializerMethodField()

    class Meta:
        model = ProjectMaterial
        fields = [
            "id",
            "materialType",
            "backingRecordId",
            "sourceProject",
            "visibility",
            "classificationState",
            "displayName",
            "actionCapabilities",
        ]

    def get_sourceProject(self, obj):
        return {"id": str(obj.source_project_id), "title": obj.source_project.title}

    def get_displayName(self, obj):
        return project_material_display_name(obj)

    def get_actionCapabilities(self, obj):
        request = self.context.get("request")
        return project_material_capabilities(getattr(request, "user", None), obj)


class ProjectMaterialCreateSerializer(serializers.Serializer):
    materialType = serializers.ChoiceField(choices=ProjectMaterial.MaterialType.values)
    file = serializers.FileField()
    title = serializers.CharField(max_length=255, required=False, allow_blank=True)
    visibility = serializers.ChoiceField(
        choices=ProjectMaterial.VisibilityState.values,
        required=False,
        default=ProjectMaterial.VisibilityState.PROJECT_ONLY,
    )

    def to_internal_value(self, data):
        attrs = super().to_internal_value(data)
        attrs["material_type"] = attrs.pop("materialType")
        attrs["upload"] = attrs.pop("file")
        return attrs


class ProjectMaterialVisibilitySerializer(serializers.Serializer):
    visibility = serializers.ChoiceField(choices=ProjectMaterial.VisibilityState.values)
    reason = serializers.CharField(required=False, allow_blank=True)


class ProjectDashboardSerializer(ProjectSerializer):
    current_tasks = serializers.SerializerMethodField()
    pending_reviews = serializers.SerializerMethodField()

    class Meta(ProjectSerializer.Meta):
        fields = ProjectSerializer.Meta.fields + [
            "current_tasks",
            "pending_reviews",
        ]

    @extend_schema_field(serializers.ListField(child=serializers.DictField()))
    def get_current_tasks(self, obj):
        from apps.tasks.serializers import TaskSerializer

        tasks = obj.tasks.exclude(status__in=["completed", "cancelled"]).order_by(
            "parent_task_id", "id"
        )[:20]
        return TaskSerializer(
            tasks,
            many=True,
        ).data

    @extend_schema_field(serializers.ListField(child=serializers.DictField()))
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
        download_events = [
            {
                "source": "download",
                "event_type": "download." + event.target_type,
                "summary": f"Downloaded {event.filename}",
                "actor_id": event.actor_id,
                "created_at": event.downloaded_at,
            }
            for event in instance.download_events.select_related("actor")[:20]
        ]
        data["activity"] = sorted(
            [*audit_events, *comment_events, *notification_events, *download_events],
            key=lambda item: item["created_at"],
            reverse=True,
        )[:20]
        return data
