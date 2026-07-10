from django.core.exceptions import PermissionDenied as DjangoPermissionDenied
from django.core.exceptions import ValidationError as DjangoValidationError
from django.shortcuts import get_object_or_404
from drf_spectacular.utils import OpenApiResponse, extend_schema
from rest_framework import mixins, status, views, viewsets
from rest_framework.decorators import action
from rest_framework.exceptions import PermissionDenied, ValidationError
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from apps.common.downloads import DownloadUnavailable, storage_file_download_response
from apps.common.search import apply_text_search
from apps.projects.services import projects_visible_to

from .comment_services import InlineCommentService
from .draft_services import DraftService
from .feedback_services import TeacherFeedbackService
from .models import (
    Draft,
    DraftVersion,
    InlineComment,
    TeacherFeedback,
    WeeklyProgressReport,
    WritingProject,
    WritingVersion,
)
from .report_services import WeeklyReportService
from .serializers import (
    DraftSerializer,
    DraftVersionSerializer,
    InlineCommentSerializer,
    InlineCommentStatusSerializer,
    ReviewStatusSerializer,
    TeacherFeedbackCreateSerializer,
    TeacherFeedbackSerializer,
    WeeklyReportSerializer,
    WritingProjectCreateSerializer,
    WritingProjectSerializer,
    WritingVersionSerializer,
    WritingVersionUploadSerializer,
)
from .writing_participant_services import writing_projects_for_user
from .writing_services import (
    WritingProjectService,
    create_standalone_writing_project,
    upload_standalone_writing_version,
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

    @extend_schema(
        request=DraftVersionSerializer,
        responses={
            201: DraftVersionSerializer,
            403: OpenApiResponse(description="Draft submission forbidden"),
        },
    )
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
    mixins.CreateModelMixin, mixins.ListModelMixin, viewsets.GenericViewSet
):
    permission_classes = [IsAuthenticated]

    def get_project(self):
        return get_object_or_404(
            projects_visible_to(self.request.user), pk=self.kwargs["project_id"]
        )

    def get_serializer_class(self):
        if self.action == "create":
            return WritingProjectCreateSerializer
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


class StandaloneWritingProjectViewSet(
    mixins.CreateModelMixin, mixins.ListModelMixin, viewsets.GenericViewSet
):
    permission_classes = [IsAuthenticated]

    def get_serializer_class(self):
        if self.action == "create":
            return WritingProjectCreateSerializer
        return WritingProjectSerializer

    def get_queryset(self):
        queryset = writing_projects_for_user(self.request.user)
        query = self.request.query_params.get("q") or self.request.query_params.get("search")
        if query:
            queryset = apply_text_search(queryset, query, ["title"])
        status_filter = self.request.query_params.get("status")
        if status_filter:
            queryset = queryset.filter(status=status_filter)
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
                request.user,
                writing_project=writing_project, **serializer.validated_data
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


class TeacherFeedbackDownloadView(views.APIView):
    permission_classes = [IsAuthenticated]

    @extend_schema(
        responses={
            200: OpenApiResponse(description="Download descriptor"),
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
        try:
            TeacherFeedbackService(request.user, project).describe_feedback_download(feedback)
        except DjangoPermissionDenied as exc:
            raise PermissionDenied(str(exc)) from exc
        try:
            return storage_file_download_response(
                feedback.annotated_file.stored_name,
                filename=feedback.annotated_file.original_filename,
                content_type=feedback.annotated_file.content_type or "application/octet-stream",
            )
        except DownloadUnavailable as exc:
            return Response({"message": str(exc)}, status=status.HTTP_410_GONE)
