from drf_spectacular.utils import extend_schema_field
from rest_framework import serializers

from .models import Task


class TaskSerializer(serializers.ModelSerializer):
    children = serializers.SerializerMethodField()
    parent_task_id = serializers.IntegerField(required=False, allow_null=True)
    assignee_id = serializers.IntegerField(required=False, allow_null=True)

    class Meta:
        model = Task
        fields = [
            "id",
            "project_id",
            "parent_task_id",
            "title",
            "description",
            "assignee_id",
            "status",
            "priority",
            "deadline_at",
            "children",
        ]
        read_only_fields = ["project_id", "children"]

    @extend_schema_field(serializers.ListField(child=serializers.DictField()))
    def get_children(self, obj):
        return TaskSerializer(obj.children.all(), many=True).data
