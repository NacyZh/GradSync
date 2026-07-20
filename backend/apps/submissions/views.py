from django.core.exceptions import PermissionDenied as DjangoPermissionDenied
from django.core.exceptions import ValidationError as DjangoValidationError
from django.shortcuts import get_object_or_404
from drf_spectacular.utils import OpenApiResponse, extend_schema
from rest_framework import mixins, serializers, status, views, viewsets
from rest_framework.decorators import action
from rest_framework.exceptions import PermissionDenied, ValidationError
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from apps.common.downloads import DownloadUnavailable, storage_file_download_response
from apps.common.search import apply_text_search
from apps.projects.services import projects_visible_to

from .comment_services import InlineCommentService
from .feedback_services import TeacherFeedbackService
from .models import (
    InlineComment,
    ProjectReportSchedule,
    TeacherFeedback,
    WeeklyProgressReport,
    WritingProject,
    WritingVersion,
)
from .report_services import WeeklyReportService
from .serializers import (
    InlineCommentSerializer,
    InlineCommentStatusSerializer,
    ProjectReportScheduleSerializer,
    ProjectReportScheduleWriteSerializer,
    ReviewStatusSerializer,
    TeacherFeedbackCreateSerializer,
    TeacherFeedbackSerializer,
    WeeklyReportSerializer,
    WritingProjectCreateSerializer,
    WritingProjectRenameSerializer,
    WritingProjectSerializer,
    WritingVersionSerializer,
    WritingVersionUploadSerializer,
)
from .services import (
    ReportScheduleVersionConflict,
    configure_project_report_schedule,
    remove_project_report_schedule,
)
from .writing_participant_services import writing_projects_for_user
from .writing_services import (
    WritingProjectService,
    archive_writing_project,
    create_standalone_writing_project,
    record_writing_version_download,
    rename_writing_project,
    require_writing_version_download_access,
    upload_standalone_writing_version,
)


class WeeklyReportViewSet(mixins.CreateModelMixin, mixins.ListModelMixin, viewsets.GenericViewSet):
    serializer_class = WeeklyReportSerializer
    permission_classes = [IsAuthenticated]

    @extend_schema(
        request=WeeklyReportSerializer,
        responses={
            201: WeeklyReportSerializer,
            409: OpenApiResponse(description="Duplicate weekly report"),
        },
    )
    def create(self, request, *args, **kwargs):
        return super().create(request, *args, **kwargs)

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


class ProjectReportScheduleView(views.APIView):
    serializer_class = ProjectReportScheduleSerializer
    permission_classes = [IsAuthenticated]

    def get_project(self, request, project_id):
        return get_object_or_404(projects_visible_to(request.user), pk=project_id)

    def get(self, request, project_id):
        project = self.get_project(request, project_id)
        policy = (
            ProjectReportSchedule.objects.select_related("updated_by")
            .filter(project=project)
            .first()
        )
        if policy is None:
            return Response(status=status.HTTP_204_NO_CONTENT)
        return Response(ProjectReportScheduleSerializer(policy).data)

    def put(self, request, project_id):
        project = self.get_project(request, project_id)
        serializer = ProjectReportScheduleWriteSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data
        try:
            policy = configure_project_report_schedule(
                actor=request.user,
                project=project,
                weekday=data["weekday"],
                deadline_time=data["deadlineLocalTime"],
                timezone_name=data["timezone"],
                expected_version=data.get("expectedVersion"),
            )
        except DjangoPermissionDenied as exc:
            raise PermissionDenied(str(exc)) from exc
        except DjangoValidationError as exc:
            raise ValidationError({"project": exc.messages}) from exc
        except ReportScheduleVersionConflict as exc:
            return Response(
                {
                    "code": "version_conflict",
                    "message": str(exc),
                    "currentVersion": exc.current.version,
                    "current": ProjectReportScheduleSerializer(exc.current).data,
                },
                status=status.HTTP_409_CONFLICT,
            )
        return Response(ProjectReportScheduleSerializer(policy).data)

    def delete(self, request, project_id):
        project = self.get_project(request, project_id)
        serializer = serializers.Serializer(data=request.data)
        serializer.fields["expectedVersion"] = serializers.IntegerField(min_value=1)
        serializer.is_valid(raise_exception=True)
        try:
            remove_project_report_schedule(
                actor=request.user,
                project=project,
                expected_version=serializer.validated_data["expectedVersion"],
            )
        except DjangoPermissionDenied as exc:
            raise PermissionDenied(str(exc)) from exc
        except ReportScheduleVersionConflict as exc:
            return Response(
                {
                    "code": "version_conflict",
                    "message": str(exc),
                    "currentVersion": exc.current.version,
                },
                status=status.HTTP_409_CONFLICT,
            )
        return Response(status=status.HTTP_204_NO_CONTENT)


class InlineCommentViewSet(
    mixins.CreateModelMixin, mixins.ListModelMixin, mixins.UpdateModelMixin, viewsets.GenericViewSet
):
    serializer_class = InlineCommentSerializer
    permission_classes = [IsAuthenticated]

    @extend_schema(
        request=InlineCommentSerializer,
        responses={
            201: InlineCommentSerializer,
            422: OpenApiResponse(description="Validation error"),
        },
    )
    def create(self, request, *args, **kwargs):
        return super().create(request, *args, **kwargs)

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


def _error_message(exc: DjangoValidationError) -> str:
    if hasattr(exc, "message_dict"):
        first_value = next(iter(exc.message_dict.values()))
        if isinstance(first_value, list):
            return str(first_value[0])
        return str(first_value)
    return str(exc.messages[0] if exc.messages else exc)


class WritingProjectViewSet(
    mixins.CreateModelMixin,
    mixins.DestroyModelMixin,
    mixins.ListModelMixin,
    mixins.UpdateModelMixin,
    viewsets.GenericViewSet,
):
    permission_classes = [IsAuthenticated]

    def get_project(self):
        return get_object_or_404(
            projects_visible_to(self.request.user), pk=self.kwargs["project_id"]
        )

    def get_serializer_class(self):
        if self.action == "create":
            return WritingProjectCreateSerializer
        if self.action in {"partial_update", "update"}:
            return WritingProjectRenameSerializer
        return WritingProjectSerializer

    def get_queryset(self):
        project = self.get_project()
        queryset = (
            WritingProject.objects.filter(project=project)
            .select_related("student", "project")
            .prefetch_related(
                "versions__draft_file",
                "versions__feedback__annotated_file",
                "versions__feedback__notification",
            )
        )
        if project.memberships.filter(
            user=self.request.user, status="active", role="student"
        ).exists():
            queryset = queryset.filter(student=self.request.user)
        query = self.request.query_params.get("q")
        if query:
            queryset = apply_text_search(queryset, query, ["title"])
        status_filter = self.request.query_params.get("status")
        if status_filter:
            queryset = queryset.filter(status=status_filter)
        else:
            queryset = queryset.exclude(status=WritingProject.Status.ARCHIVED)
        return queryset

    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        try:
            writing_project = WritingProjectService(
                request.user, self.get_project()
            ).create_project(
                **serializer.validated_data,
            )
        except DjangoValidationError as exc:
            return Response({"message": _error_message(exc)}, status=status.HTTP_400_BAD_REQUEST)
        except DjangoPermissionDenied as exc:
            raise PermissionDenied(str(exc)) from exc
        return Response(
            WritingProjectSerializer(writing_project, context={"request": request}).data,
            status=status.HTTP_201_CREATED,
        )

    def partial_update(self, request, *args, **kwargs):
        writing_project = self.get_object()
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        try:
            renamed = rename_writing_project(
                request.user, writing_project, title=serializer.validated_data["title"]
            )
        except DjangoValidationError as exc:
            return Response({"message": _error_message(exc)}, status=status.HTTP_400_BAD_REQUEST)
        except DjangoPermissionDenied as exc:
            raise PermissionDenied(str(exc)) from exc
        return Response(WritingProjectSerializer(renamed, context={"request": request}).data)

    def update(self, request, *args, **kwargs):
        return self.partial_update(request, *args, **kwargs)

    def destroy(self, request, *args, **kwargs):
        try:
            archive_writing_project(request.user, self.get_object())
        except DjangoPermissionDenied as exc:
            raise PermissionDenied(str(exc)) from exc
        return Response(status=status.HTTP_204_NO_CONTENT)


class StandaloneWritingProjectViewSet(
    mixins.CreateModelMixin,
    mixins.DestroyModelMixin,
    mixins.ListModelMixin,
    mixins.UpdateModelMixin,
    viewsets.GenericViewSet,
):
    permission_classes = [IsAuthenticated]

    def get_serializer_class(self):
        if self.action == "create":
            return WritingProjectCreateSerializer
        if self.action in {"partial_update", "update"}:
            return WritingProjectRenameSerializer
        return WritingProjectSerializer

    def get_queryset(self):
        queryset = writing_projects_for_user(self.request.user)
        query = self.request.query_params.get("q") or self.request.query_params.get("search")
        if query:
            queryset = apply_text_search(queryset, query, ["title"])
        status_filter = self.request.query_params.get("status")
        if status_filter:
            queryset = queryset.filter(status=status_filter)
        else:
            queryset = queryset.exclude(status=WritingProject.Status.ARCHIVED)
        return queryset

    def list(self, request, *args, **kwargs):
        queryset = self.filter_queryset(self.get_queryset())
        return Response(
            {
                "results": WritingProjectSerializer(
                    queryset, many=True, context={"request": request}
                ).data
            }
        )

    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        try:
            writing_project = create_standalone_writing_project(
                request.user, **serializer.validated_data
            )
        except DjangoValidationError as exc:
            return Response({"message": _error_message(exc)}, status=status.HTTP_400_BAD_REQUEST)
        except DjangoPermissionDenied as exc:
            raise PermissionDenied(str(exc)) from exc
        return Response(
            WritingProjectSerializer(writing_project, context={"request": request}).data,
            status=status.HTTP_201_CREATED,
        )

    def partial_update(self, request, *args, **kwargs):
        writing_project = self.get_object()
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        try:
            renamed = rename_writing_project(
                request.user, writing_project, title=serializer.validated_data["title"]
            )
        except DjangoValidationError as exc:
            return Response({"message": _error_message(exc)}, status=status.HTTP_400_BAD_REQUEST)
        except DjangoPermissionDenied as exc:
            raise PermissionDenied(str(exc)) from exc
        return Response(WritingProjectSerializer(renamed, context={"request": request}).data)

    def update(self, request, *args, **kwargs):
        return self.partial_update(request, *args, **kwargs)

    def destroy(self, request, *args, **kwargs):
        try:
            archive_writing_project(request.user, self.get_object())
        except DjangoPermissionDenied as exc:
            raise PermissionDenied(str(exc)) from exc
        return Response(status=status.HTTP_204_NO_CONTENT)


class WritingVersionUploadView(views.APIView):
    permission_classes = [IsAuthenticated]

    @extend_schema(
        request={"multipart/form-data": WritingVersionUploadSerializer},
        responses={201: WritingVersionSerializer},
    )
    def post(self, request, writing_project_id):
        writing_project = get_object_or_404(
            WritingProject.objects.select_related("project", "student"),
            pk=writing_project_id,
        )
        serializer = WritingVersionUploadSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        try:
            version = upload_standalone_writing_version(
                request.user, writing_project=writing_project, **serializer.validated_data
            )
        except DjangoValidationError as exc:
            return Response({"message": _error_message(exc)}, status=status.HTTP_400_BAD_REQUEST)
        except DjangoPermissionDenied as exc:
            raise PermissionDenied(str(exc)) from exc
        return Response(WritingVersionSerializer(version).data, status=status.HTTP_201_CREATED)


class TeacherFeedbackSubmitView(views.APIView):
    permission_classes = [IsAuthenticated]

    @extend_schema(
        request={"multipart/form-data": TeacherFeedbackCreateSerializer},
        responses={201: TeacherFeedbackSerializer},
    )
    def post(self, request, writing_version_id):
        version = get_object_or_404(
            WritingVersion.objects.select_related(
                "writing_project__project", "writing_project__student"
            ),
            pk=writing_version_id,
        )
        serializer = TeacherFeedbackCreateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        try:
            feedback = TeacherFeedbackService(
                request.user, version.writing_project.project
            ).submit_feedback(writing_version=version, **serializer.validated_data)
        except DjangoValidationError as exc:
            return Response({"message": _error_message(exc)}, status=status.HTTP_400_BAD_REQUEST)
        except DjangoPermissionDenied as exc:
            raise PermissionDenied(str(exc)) from exc
        return Response(TeacherFeedbackSerializer(feedback).data, status=status.HTTP_201_CREATED)


class WritingVersionDownloadView(views.APIView):
    permission_classes = [IsAuthenticated]

    @extend_schema(
        responses={
            200: OpenApiResponse(description="Writing version file download"),
            403: OpenApiResponse(description="Download forbidden"),
            410: OpenApiResponse(description="Writing version file is unavailable"),
        }
    )
    def get(self, request, writing_version_id):
        version = get_object_or_404(
            WritingVersion.objects.select_related(
                "draft_file",
                "writing_project__project",
                "writing_project__legacy_project",
                "writing_project__student",
            ),
            pk=writing_version_id,
        )
        try:
            require_writing_version_download_access(request.user, version)
        except DjangoPermissionDenied as exc:
            raise PermissionDenied(str(exc)) from exc
        try:
            response = storage_file_download_response(
                version.draft_file.stored_name,
                filename=version.draft_file.original_filename,
                content_type=version.draft_file.content_type or "application/octet-stream",
            )
        except DownloadUnavailable as exc:
            return Response({"message": str(exc)}, status=status.HTTP_410_GONE)
        record_writing_version_download(request.user, version)
        return response


class TeacherFeedbackDownloadView(views.APIView):
    permission_classes = [IsAuthenticated]

    @extend_schema(
        responses={
            200: OpenApiResponse(description="Annotated feedback file download"),
            403: OpenApiResponse(description="Download forbidden"),
        }
    )
    def get(self, request, feedback_id):
        feedback = get_object_or_404(
            TeacherFeedback.objects.select_related(
                "annotated_file",
                "writing_version__writing_project__project",
                "writing_version__writing_project__student",
            ),
            pk=feedback_id,
        )
        project = feedback.writing_version.writing_project.project
        service = TeacherFeedbackService(request.user, project)
        try:
            service.require_feedback_download_access(feedback)
        except DjangoPermissionDenied as exc:
            raise PermissionDenied(str(exc)) from exc
        try:
            response = storage_file_download_response(
                feedback.annotated_file.stored_name,
                filename=feedback.annotated_file.original_filename,
                content_type=feedback.annotated_file.content_type or "application/octet-stream",
            )
        except DownloadUnavailable as exc:
            return Response({"message": str(exc)}, status=status.HTTP_410_GONE)
        service.record_feedback_download(feedback)
        return response
