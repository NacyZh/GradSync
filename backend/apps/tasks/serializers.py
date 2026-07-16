from drf_spectacular.utils import extend_schema_field
from rest_framework import serializers

from .models import Task


class TaskSerializer(serializers.ModelSerializer):
    children = serializers.SerializerMethodField()
    parent_task_id = serializers.IntegerField(required=False, allow_null=True)
    assignee_id = serializers.IntegerField(required=False, allow_null=True)
    assignee_ids = serializers.ListField(
        child=serializers.IntegerField(), required=False, allow_empty=True
    )

    class Meta:
        model = Task
        fields = [
            "id",
            "project_id",
            "parent_task_id",
            "title",
            "description",
            "assignee_id",
            "assignee_ids",
            "status",
            "priority",
            "deadline_at",
            "children",
        ]
        read_only_fields = ["project_id", "children"]

    def to_representation(self, instance):
        data = super().to_representation(instance)
        assignee_ids = list(instance.assignees.values_list("id", flat=True))
        if not assignee_ids and instance.assignee_id:
            assignee_ids = [instance.assignee_id]
        data["assignee_ids"] = assignee_ids
        return data

    @extend_schema_field(serializers.ListField(child=serializers.DictField()))
    def get_children(self, obj):
        return TaskSerializer(obj.children.all(), many=True).data
