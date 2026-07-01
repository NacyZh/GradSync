from django.core.exceptions import ValidationError as DjangoValidationError
from django.shortcuts import get_object_or_404
from rest_framework import mixins, viewsets
from rest_framework.exceptions import ValidationError
from rest_framework.permissions import IsAuthenticated

from apps.common.search import apply_text_search
from apps.projects.services import projects_visible_to

from .models import Task
from .serializers import TaskSerializer
from .services import TaskService


class ProjectTaskViewSet(
    mixins.CreateModelMixin, mixins.ListModelMixin, mixins.UpdateModelMixin, viewsets.GenericViewSet
):
    serializer_class = TaskSerializer
    permission_classes = [IsAuthenticated]

    def get_project(self):
        return get_object_or_404(
            projects_visible_to(self.request.user), pk=self.kwargs["project_id"]
        )

    def get_queryset(self):
        project = self.get_project()
        queryset = Task.objects.filter(project=project)
        queryset = apply_text_search(
            queryset, self.request.query_params.get("search"), ["title", "description"]
        )
        for field in ["status", "priority", "assignee_id"]:
            value = self.request.query_params.get(field)
            if value:
                queryset = queryset.filter(**{field: value})
        if self.action == "list" and not self.request.query_params.get("include_children"):
            queryset = queryset.filter(parent_task__isnull=True)
        return queryset.prefetch_related("children")

    def perform_create(self, serializer):
        try:
            project = self.get_project()
            task = TaskService(self.request.user, project).create_task(**serializer.validated_data)
            serializer.instance = task
        except DjangoValidationError as exc:
            raise ValidationError(
                exc.message_dict if hasattr(exc, "message_dict") else exc.messages
            ) from exc

    def perform_update(self, serializer):
        try:
            project = self.get_project()
            task = TaskService(self.request.user, project).update_task(
                serializer.instance, **serializer.validated_data
            )
            serializer.instance = task
        except DjangoValidationError as exc:
            raise ValidationError(
                exc.message_dict if hasattr(exc, "message_dict") else exc.messages
            ) from exc
