from django.core.exceptions import ValidationError as DjangoValidationError
from django.db.models import Q
from django.shortcuts import get_object_or_404
from rest_framework import mixins, status, viewsets
from rest_framework.decorators import action
from rest_framework.exceptions import PermissionDenied, ValidationError
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from apps.common.downloads import describe_paper_download
from apps.projects.services import projects_visible_to

from .import_services import PaperImportService
from .models import PaperImportBatch, PaperRecord
from .serializers import (
    PaperImportBatchSerializer,
    PaperImportSerializer,
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
        return get_object_or_404(projects_visible_to(self.request.user), pk=self.kwargs["project_id"])

    def get_queryset(self):
        project = self.get_project()
        queryset = PaperRecord.objects.filter(project=project).prefetch_related("attachments")
        query = self.request.query_params.get("q")
        if query:
            queryset = queryset.filter(
                Q(title__icontains=query)
                | Q(venue__icontains=query)
                | Q(doi__icontains=query)
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
        return queryset

    def get_serializer_class(self):
        if self.action == "create":
            return PaperRecordCreateSerializer
        return PaperRecordSerializer

    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        try:
            paper = PaperImportService(request.user, self.get_project()).create_paper(
                **serializer.validated_data
            )
        except DjangoValidationError as exc:
            detail = exc.message_dict if hasattr(exc, "message_dict") else exc.messages
            detail = _flatten_error_detail(detail)
            status_code = status.HTTP_409_CONFLICT if isinstance(detail, dict) else status.HTTP_400_BAD_REQUEST
            return Response(detail, status=status_code)
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
