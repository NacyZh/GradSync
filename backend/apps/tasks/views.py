from django.core.exceptions import ValidationError as DjangoValidationError
from django.shortcuts import get_object_or_404
from drf_spectacular.utils import OpenApiResponse, extend_schema
from rest_framework import mixins, status, viewsets
from rest_framework.exceptions import ValidationError
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from apps.common.search import apply_text_search
from apps.projects.services import projects_visible_to

from .models import Task
from .serializers import TaskSerializer
from .services import TaskService


class ProjectTaskViewSet(
    mixins.CreateModelMixin,
    mixins.ListModelMixin,
    mixins.UpdateModelMixin,
    mixins.DestroyModelMixin,
    viewsets.GenericViewSet,
):
    serializer_class = TaskSerializer
    permission_classes = [IsAuthenticated]

    @extend_schema(
        request=TaskSerializer,
        responses={
            201: TaskSerializer,
            422: OpenApiResponse(description="Validation error"),
        },
    )
    def create(self, request, *args, **kwargs):
        return super().create(request, *args, **kwargs)

    @extend_schema(
        request=TaskSerializer,
        responses={
            200: TaskSerializer,
            403: OpenApiResponse(description="Task update forbidden"),
            422: OpenApiResponse(description="Validation error"),
        },
    )
    def partial_update(self, request, *args, **kwargs):
        return super().partial_update(request, *args, **kwargs)

    @extend_schema(
        responses={
            204: OpenApiResponse(description="Task deleted"),
            403: OpenApiResponse(description="Task deletion forbidden"),
        },
    )
    def destroy(self, request, *args, **kwargs):
        try:
            project = self.get_project()
            TaskService(request.user, project).delete_task(self.get_object())
            return Response(status=status.HTTP_204_NO_CONTENT)
        except DjangoValidationError as exc:
            raise ValidationError(
                exc.message_dict if hasattr(exc, "message_dict") else exc.messages
            ) from exc

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
        return queryset.prefetch_related("assignees", "children")

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
