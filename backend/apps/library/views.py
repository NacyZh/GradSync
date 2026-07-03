from django.core.exceptions import PermissionDenied as DjangoPermissionDenied
from django.core.exceptions import ValidationError as DjangoValidationError
from django.db.models import Q
from django.shortcuts import get_object_or_404
from rest_framework import mixins, status, views, viewsets
from rest_framework.decorators import action
from rest_framework.exceptions import PermissionDenied, ValidationError
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from apps.common.downloads import describe_paper_download
from apps.common.project_scope import visible_asset_q
from apps.projects.models import ResearchProject

from .import_services import PaperImportService
from .models import PaperImportBatch, PaperRecord
from .serializers import (
    PaperImportBatchSerializer,
    PaperImportSerializer,
    PaperUploadSerializer,
    PaperRecordCreateSerializer,
    PaperRecordSerializer,
)


def _flatten_error_detail(detail):
    if isinstance(detail, dict):
        return {
            key: value[0] if isinstance(value, list) and len(value) == 1 else value
            for key, value in detail.items()
        }
    return detail


class PaperViewSet(mixins.ListModelMixin, mixins.CreateModelMixin, viewsets.GenericViewSet):
    permission_classes = [IsAuthenticated]

    def get_project(self):
        return get_object_or_404(ResearchProject.objects.all(), pk=self.kwargs["project_id"])

    def get_queryset(self):
        project = self.get_project()
        queryset = (
            PaperRecord.objects.filter(project=project)
            .filter(visible_asset_q(self.request.user))
            .select_related("uploaded_file", "project")
            .prefetch_related("attachments")
            .distinct()
        )
        query = self.request.query_params.get("q")
        if query:
            queryset = queryset.filter(
                Q(title__icontains=query)
                | Q(venue__icontains=query)
                | Q(doi__icontains=query)
                | Q(abstract__icontains=query)
                | Q(authors__icontains=query)
                | Q(tags__icontains=query)
            )
        tag = self.request.query_params.get("tag")
        if tag:
            queryset = queryset.filter(tags__icontains=tag)
        year = self.request.query_params.get("year")
        if year:
            queryset = queryset.filter(publication_year=year)
        author = self.request.query_params.get("author")
        if author:
            queryset = queryset.filter(authors__icontains=author)
        visibility = self.request.query_params.get("visibility")
        if visibility:
            queryset = queryset.filter(visibility=visibility)
        return queryset

    def get_serializer_class(self):
        if self.action == "create":
            if "file" in self.request.data:
                return PaperUploadSerializer
            return PaperRecordCreateSerializer
        return PaperRecordSerializer

    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        try:
            service = PaperImportService(request.user, self.get_project())
            if "upload" in serializer.validated_data:
                paper = service.upload_paper(**serializer.validated_data)
            else:
                paper = service.create_paper(**serializer.validated_data)
        except DjangoValidationError as exc:
            detail = exc.message_dict if hasattr(exc, "message_dict") else exc.messages
            detail = _flatten_error_detail(detail)
            status_code = (
                status.HTTP_409_CONFLICT
                if isinstance(detail, dict)
                else status.HTTP_400_BAD_REQUEST
            )
            return Response(detail, status=status_code)
        except (PermissionError, DjangoPermissionDenied) as exc:
            raise PermissionDenied(str(exc)) from exc
        return Response(PaperRecordSerializer(paper).data, status=status.HTTP_201_CREATED)

    @action(detail=False, methods=["post"], url_path="imports")
    def imports(self, request, project_id=None):
        serializer = PaperImportSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        try:
            batch = PaperImportService(request.user, self.get_project()).stage_import(
                **serializer.validated_data
            )
        except DjangoValidationError as exc:
            raise ValidationError(exc.messages) from exc
        return Response(PaperImportBatchSerializer(batch).data, status=status.HTTP_201_CREATED)

    @action(
        detail=False,
        methods=["post"],
        url_path=r"imports/(?P<batch_id>[^/.]+)/commit",
    )
    def commit_import(self, request, project_id=None, batch_id=None):
        batch = get_object_or_404(PaperImportBatch, project=self.get_project(), pk=batch_id)
        try:
            batch = PaperImportService(request.user, self.get_project()).commit_import(batch)
        except DjangoValidationError as exc:
            raise ValidationError(exc.messages) from exc
        return Response(PaperImportBatchSerializer(batch).data)

    @action(detail=True, methods=["post"], url_path="download")
    def download(self, request, project_id=None, pk=None):
        paper = get_object_or_404(PaperRecord, project=self.get_project(), pk=pk)
        try:
            return Response(describe_paper_download(request.user, paper))
        except PermissionError as exc:
            raise PermissionDenied(str(exc)) from exc


class PaperDownloadView(views.APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request, paper_id):
        paper = get_object_or_404(PaperRecord.objects.select_related("project", "uploaded_file"), pk=paper_id)
        try:
            return Response(describe_paper_download(request.user, paper))
        except PermissionError as exc:
            raise PermissionDenied(str(exc)) from exc
