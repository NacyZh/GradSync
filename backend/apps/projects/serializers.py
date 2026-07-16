from django.utils import timezone
from drf_spectacular.utils import extend_schema_field
from rest_framework import serializers

from .material_services import (
    project_material_capabilities,
    project_material_display_name,
)
from .models import ProjectMaterial, ProjectMembership, ResearchProject
from .services import ProjectService, project_capabilities, project_event_feed


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

    def to_internal_value(self, data):
        if hasattr(data, "copy"):
            data = data.copy()
        if "studentIds" in data and "student_ids" not in data:
            data["student_ids"] = data["studentIds"]
        return super().to_internal_value(data)

    def validate(self, attrs):
        starts_on = attrs.get("starts_on")
        ends_on = attrs.get("ends_on")
        if starts_on and ends_on and ends_on < starts_on:
            raise serializers.ValidationError("Project end date cannot be before start date")
        student_ids = attrs.get("student_ids") or []
        if len(student_ids) != len(set(student_ids)):
            raise serializers.ValidationError("Student selections must not contain duplicates")
        if student_ids:
            from django.contrib.auth import get_user_model

            user_model = get_user_model()
            students = list(user_model.objects.filter(id__in=student_ids))
            if {student.id for student in students} != set(student_ids):
                raise serializers.ValidationError("Selected student does not exist")
            for student in students:
                if (
                    student.global_role != student.GlobalRole.STUDENT
                    or student.status != student.Status.ACTIVE
                    or student.active_role != student.RequestedRole.STUDENT
                ):
                    raise serializers.ValidationError("Selected account is not an active student")
        return attrs

    def create(self, validated_data):
        return ProjectService(self.context["request"].user).create_project(**validated_data)


class ProjectSerializer(serializers.ModelSerializer):
    memberships = ProjectMembershipSerializer(many=True, read_only=True)
    advisorId = serializers.IntegerField(source="advisor_id", read_only=True)
    startsOn = serializers.DateField(source="starts_on", read_only=True)
    endsOn = serializers.DateField(source="ends_on", read_only=True)
    archivedAt = serializers.DateTimeField(source="archived_at", read_only=True)
    capabilities = serializers.SerializerMethodField()

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
            "advisorId",
            "startsOn",
            "endsOn",
            "archivedAt",
            "memberships",
            "capabilities",
        ]

    @extend_schema_field(serializers.DictField())
    def get_capabilities(self, obj):
        request = self.context.get("request")
        return project_capabilities(getattr(request, "user", None), obj)


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


class ProjectEventSerializer(serializers.Serializer):
    id = serializers.CharField()
    source = serializers.ChoiceField(choices=["audit", "download", "notification", "comment"])
    eventType = serializers.CharField()
    targetType = serializers.CharField(allow_blank=True)
    targetId = serializers.CharField(allow_blank=True)
    summary = serializers.CharField()
    actorId = serializers.IntegerField(allow_null=True)
    createdAt = serializers.DateTimeField()


class ProjectDashboardSerializer(ProjectSerializer):
    current_tasks = serializers.SerializerMethodField()
    pending_reviews = serializers.SerializerMethodField()
    latestEventId = serializers.SerializerMethodField()
    freshness = serializers.SerializerMethodField()
    generatedAt = serializers.SerializerMethodField()

    class Meta(ProjectSerializer.Meta):
        fields = ProjectSerializer.Meta.fields + [
            "current_tasks",
            "pending_reviews",
            "latestEventId",
            "freshness",
            "generatedAt",
        ]

    @extend_schema_field(serializers.ListField(child=serializers.DictField()))
    def get_current_tasks(self, obj):
        from apps.tasks.serializers import TaskSerializer

        tasks = obj.tasks.exclude(status__in=["completed", "cancelled"]).prefetch_related(
            "assignees", "children"
        ).order_by("parent_task_id", "id")[:20]
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

    def get_latestEventId(self, obj):
        events = project_event_feed(obj, limit=1)
        return events[0]["id"] if events else None

    def get_freshness(self, obj):
        return {
            "state": "fresh",
            "latestEventId": self.get_latestEventId(obj),
        }

    def get_generatedAt(self, obj):
        return timezone.now()

    def to_representation(self, instance):
        data = super().to_representation(instance)
        audit_events = [
            {
                "id": f"audit:{event.id}",
                "source": "audit",
                "event_type": event.event_type,
                "eventType": event.event_type,
                "summary": event.summary,
                "actor_id": event.actor_id,
                "actorId": event.actor_id,
                "created_at": event.created_at,
                "createdAt": event.created_at,
            }
            for event in instance.audit_events.select_related("actor")[:20]
        ]
        comment_events = [
            {
                "source": "comment",
                "event_type": "inline_comment." + comment.status,
                "eventType": "inline_comment." + comment.status,
                "summary": (
                    f"Comment on {comment.target_type} {comment.target_id}: {comment.anchor}"
                ),
                "actor_id": comment.author_id,
                "actorId": comment.author_id,
                "created_at": comment.created_at,
                "createdAt": comment.created_at,
            }
            for comment in instance.inline_comments.select_related("author")[:20]
        ]
        notification_events = [
            {
                "source": "notification",
                "event_type": "notification." + notification.status,
                "eventType": "notification." + notification.status,
                "summary": notification.subject,
                "actor_id": notification.sender_id,
                "actorId": notification.sender_id,
                "created_at": notification.created_at,
                "createdAt": notification.created_at,
            }
            for notification in instance.notifications.select_related("sender")[:20]
        ]
        download_events = [
            {
                "id": f"download:{event.id}",
                "source": "download",
                "event_type": "download." + event.target_type,
                "eventType": "download." + event.target_type,
                "summary": f"Downloaded {event.filename}",
                "actor_id": event.actor_id,
                "actorId": event.actor_id,
                "created_at": event.downloaded_at,
                "createdAt": event.downloaded_at,
            }
            for event in instance.download_events.select_related("actor")[:20]
        ]
        data["activity"] = sorted(
            [*audit_events, *comment_events, *notification_events, *download_events],
            key=lambda item: item["created_at"],
            reverse=True,
        )[:20]
        return data
