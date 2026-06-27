from django.core.exceptions import ValidationError as DjangoValidationError
from django.shortcuts import get_object_or_404
from rest_framework import mixins, status, viewsets
from rest_framework.decorators import action
from rest_framework.exceptions import ValidationError
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from apps.common.search import apply_text_search
from apps.projects.services import projects_visible_to

from .comment_services import InlineCommentService
from .draft_services import DraftService
from .models import Draft, DraftVersion, InlineComment, WeeklyProgressReport
from .report_services import WeeklyReportService
from .serializers import (
    DraftSerializer,
    DraftVersionSerializer,
    InlineCommentSerializer,
    InlineCommentStatusSerializer,
    ReviewStatusSerializer,
    WeeklyReportSerializer,
)


class DraftViewSet(mixins.CreateModelMixin, mixins.ListModelMixin, viewsets.GenericViewSet):
    serializer_class = DraftSerializer
    permission_classes = [IsAuthenticated]

    def get_project(self):
        return get_object_or_404(
            projects_visible_to(self.request.user), pk=self.kwargs["project_id"]
        )

    def get_queryset(self):
        queryset = Draft.objects.filter(project=self.get_project()).prefetch_related("versions")
        queryset = apply_text_search(queryset, self.request.query_params.get("search"), ["title"])
        status_filter = self.request.query_params.get("status")
        if status_filter:
            queryset = queryset.filter(status=status_filter)
        return queryset

    def perform_create(self, serializer):
        draft = DraftService(self.request.user, self.get_project()).create_draft(
            **serializer.validated_data
        )
        serializer.instance = draft

    @action(detail=True, methods=["post"], url_path="versions")
    def submit_version(self, request, project_id=None, pk=None):
        project = self.get_project()
        draft = get_object_or_404(Draft, project=project, pk=pk)
        serializer = DraftVersionSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        version = DraftService(request.user, project).submit_version(
            draft=draft, **serializer.validated_data
        )
        return Response(DraftVersionSerializer(version).data, status=status.HTTP_201_CREATED)

    @action(detail=True, methods=["patch"], url_path="versions/(?P<version_id>[^/.]+)/review")
    def review_version(self, request, project_id=None, pk=None, version_id=None):
        project = self.get_project()
        draft = get_object_or_404(Draft, project=project, pk=pk)
        version = get_object_or_404(DraftVersion, project=project, draft=draft, pk=version_id)
        serializer = ReviewStatusSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        version = DraftService(request.user, project).update_review_status(
            version, serializer.validated_data["review_status"]
        )
        return Response(DraftVersionSerializer(version).data)


class WeeklyReportViewSet(mixins.CreateModelMixin, mixins.ListModelMixin, viewsets.GenericViewSet):
    serializer_class = WeeklyReportSerializer
    permission_classes = [IsAuthenticated]

    def get_project(self):
        return get_object_or_404(
            projects_visible_to(self.request.user), pk=self.kwargs["project_id"]
        )

    def get_queryset(self):
        queryset = WeeklyProgressReport.objects.filter(project=self.get_project())
        queryset = apply_text_search(
            queryset,
            self.request.query_params.get("search"),
            ["completed_work", "blockers", "next_steps"],
        )
        status_filter = self.request.query_params.get("review_status")
        if status_filter:
            queryset = queryset.filter(review_status=status_filter)
        return queryset

    def perform_create(self, serializer):
        try:
            report = WeeklyReportService(self.request.user, self.get_project()).submit_report(
                **serializer.validated_data
            )
        except DjangoValidationError as exc:
            raise ValidationError(exc.messages) from exc
        serializer.instance = report

    @action(detail=True, methods=["patch"], url_path="review")
    def review_report(self, request, project_id=None, pk=None):
        project = self.get_project()
        report = get_object_or_404(WeeklyProgressReport, project=project, pk=pk)
        serializer = ReviewStatusSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        report = WeeklyReportService(request.user, project).update_review_status(
            report, serializer.validated_data["review_status"]
        )
        return Response(WeeklyReportSerializer(report).data)


class InlineCommentViewSet(
    mixins.CreateModelMixin, mixins.ListModelMixin, mixins.UpdateModelMixin, viewsets.GenericViewSet
):
    serializer_class = InlineCommentSerializer
    permission_classes = [IsAuthenticated]

    def get_project(self):
        return get_object_or_404(
            projects_visible_to(self.request.user), pk=self.kwargs["project_id"]
        )

    def get_queryset(self):
        queryset = InlineComment.objects.filter(project=self.get_project())
        target_type = self.request.query_params.get("target_type")
        target_id = self.request.query_params.get("target_id")
        if target_type:
            queryset = queryset.filter(target_type=target_type)
        if target_id:
            queryset = queryset.filter(target_id=target_id)
        status_filter = self.request.query_params.get("status")
        if status_filter:
            queryset = queryset.filter(status=status_filter)
        queryset = apply_text_search(
            queryset, self.request.query_params.get("search"), ["anchor", "body"]
        )
        return queryset

    def perform_create(self, serializer):
        comment = InlineCommentService(self.request.user, self.get_project()).create_comment(
            **serializer.validated_data
        )
        serializer.instance = comment

    @action(detail=True, methods=["patch"], url_path="status")
    def set_status(self, request, project_id=None, pk=None):
        project = self.get_project()
        comment = get_object_or_404(InlineComment, project=project, pk=pk)
        serializer = InlineCommentStatusSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        comment = InlineCommentService(request.user, project).set_status(
            comment, serializer.validated_data["status"]
        )
        return Response(InlineCommentSerializer(comment).data)
