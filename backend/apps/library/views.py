from django.core.exceptions import PermissionDenied as DjangoPermissionDenied
from django.core.exceptions import ValidationError as DjangoValidationError
from django.db.models import Q
from django.shortcuts import get_object_or_404
from drf_spectacular.utils import OpenApiParameter, OpenApiResponse, extend_schema
from rest_framework import generics, mixins, status, views, viewsets
from rest_framework.decorators import action
from rest_framework.exceptions import PermissionDenied, ValidationError
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from apps.common.downloads import describe_document_download, describe_paper_download
from apps.common.project_scope import visible_asset_q
from apps.projects.models import ResearchProject

from .document_services import DocumentCategoryService, DocumentService
from .import_services import PaperImportService
from .models import DocumentCategory, DocumentRecord, PaperImportBatch, PaperImportJob, PaperRecord
from .serializers import (
    DocumentCategoryCreateSerializer,
    DocumentCategorySerializer,
    DocumentRecordSerializer,
    DocumentUploadSerializer,
    PaperImportBatchSerializer,
    PaperImportJobSerializer,
    PaperImportSerializer,
    PaperRecordCreateSerializer,
    PaperRecordSerializer,
    PaperUploadSerializer,
    UploadErrorSerializer,
)
from .services import apply_paper_search_filters, shared_paper_queryset_for


def _flatten_error_detail(detail):
    if isinstance(detail, dict):
        return {
            key: value[0] if isinstance(value, list) and len(value) == 1 else value
            for key, value in detail.items()
        }
    return detail


class PaperViewSet(mixins.ListModelMixin, mixins.CreateModelMixin, viewsets.GenericViewSet):
    permission_classes = [IsAuthenticated]

    @extend_schema(
        parameters=[
            OpenApiParameter("q", str, OpenApiParameter.QUERY),
            OpenApiParameter("tag", str, OpenApiParameter.QUERY),
            OpenApiParameter("year", int, OpenApiParameter.QUERY),
            OpenApiParameter("author", str, OpenApiParameter.QUERY),
            OpenApiParameter("visibility", str, OpenApiParameter.QUERY),
        ],
        responses={200: PaperRecordSerializer(many=True)},
    )
    def list(self, request, *args, **kwargs):
        return super().list(request, *args, **kwargs)

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

    @extend_schema(
        request={
            "application/json": PaperRecordCreateSerializer,
            "multipart/form-data": PaperUploadSerializer,
        },
        responses={
            201: PaperRecordSerializer,
            409: OpenApiResponse(description="Duplicate paper"),
            422: OpenApiResponse(description="Validation error"),
        },
    )
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

    @extend_schema(
        request=PaperImportSerializer,
        responses={201: PaperImportBatchSerializer},
    )
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

    @extend_schema(
        responses={
            200: OpenApiResponse(description="Download descriptor"),
            403: OpenApiResponse(description="Download forbidden"),
        }
    )
    @action(detail=True, methods=["post"], url_path="download")
    def download(self, request, project_id=None, pk=None):
        paper = get_object_or_404(PaperRecord, project=self.get_project(), pk=pk)
        try:
            return Response(describe_paper_download(request.user, paper))
        except PermissionError as exc:
            raise PermissionDenied(str(exc)) from exc


class PaperDownloadView(views.APIView):
    permission_classes = [IsAuthenticated]

    @extend_schema(
        responses={
            200: OpenApiResponse(description="Download descriptor"),
            403: OpenApiResponse(description="Download forbidden"),
        }
    )
    def get(self, request, paper_id):
        paper = get_object_or_404(
            PaperRecord.objects.select_related("project", "uploaded_file"),
            pk=paper_id,
        )
        try:
            return Response(describe_paper_download(request.user, paper))
        except PermissionError as exc:
            raise PermissionDenied(str(exc)) from exc


class SharedPaperListCreateView(generics.GenericAPIView):
    permission_classes = [IsAuthenticated]

    @extend_schema(
        parameters=[
            OpenApiParameter("q", str, OpenApiParameter.QUERY),
            OpenApiParameter("author", str, OpenApiParameter.QUERY),
            OpenApiParameter("year", int, OpenApiParameter.QUERY),
            OpenApiParameter("keyword", str, OpenApiParameter.QUERY),
        ],
        responses={200: PaperRecordSerializer(many=True), 400: UploadErrorSerializer},
    )
    def get(self, request):
        queryset = apply_paper_search_filters(
            shared_paper_queryset_for(request.user),
            request.query_params,
        )
        page = self.paginate_queryset(queryset)
        if page is not None:
            serializer = PaperRecordSerializer(page, many=True)
            return self.get_paginated_response(serializer.data)
        return Response(PaperRecordSerializer(queryset, many=True).data)

    @extend_schema(request={"multipart/form-data": None}, responses={202: PaperImportJobSerializer})
    def post(self, request):
        # Full file-selection-only import processing is implemented in US2.
        serializer = UploadErrorSerializer(
            {
                "code": "not_implemented",
                "message": "Paper import processing is not available yet.",
                "reason": "processing_error",
            }
        )
        return Response(serializer.data, status=status.HTTP_400_BAD_REQUEST)


class SharedPaperDetailView(views.APIView):
    permission_classes = [IsAuthenticated]

    @extend_schema(responses={200: PaperRecordSerializer})
    def get(self, request, paper_id):
        paper = get_object_or_404(shared_paper_queryset_for(request.user), pk=paper_id)
        return Response(PaperRecordSerializer(paper).data)


class PaperImportStatusView(views.APIView):
    permission_classes = [IsAuthenticated]

    @extend_schema(responses={200: PaperImportJobSerializer})
    def get(self, request, import_job_id):
        job = get_object_or_404(
            PaperImportJob.objects.select_related("paper_file"),
            pk=import_job_id,
        )
        is_maintainer = getattr(request.user, "is_administrator", False) or getattr(
            request.user, "is_advisor", False
        )
        if job.requested_by_id != request.user.id and not is_maintainer:
            raise PermissionDenied("You cannot view this paper import.")
        return Response(PaperImportJobSerializer(job).data)


class PaperImportReviewView(views.APIView):
    permission_classes = [IsAuthenticated]

    @extend_schema(responses={200: PaperImportJobSerializer})
    def post(self, request, import_job_id):
        is_maintainer = getattr(request.user, "is_administrator", False) or getattr(
            request.user, "is_advisor", False
        )
        if not is_maintainer:
            raise PermissionDenied("Only maintainers can review paper imports.")
        job = get_object_or_404(
            PaperImportJob.objects.select_related("paper_file"),
            pk=import_job_id,
        )
        return Response(PaperImportJobSerializer(job).data)


def _error_message(exc: DjangoValidationError) -> str:
    if hasattr(exc, "message_dict"):
        first_value = next(iter(exc.message_dict.values()))
        if isinstance(first_value, list):
            return str(first_value[0])
        return str(first_value)
    return str(exc.messages[0] if exc.messages else exc)


class DocumentCategoryView(views.APIView):
    permission_classes = [IsAuthenticated]

    @extend_schema(responses={200: DocumentCategorySerializer(many=True)})
    def get(self, request):
        categories = DocumentCategory.objects.filter(status=DocumentCategory.Status.ACTIVE)
        return Response(DocumentCategorySerializer(categories, many=True).data)

    @extend_schema(
        request=DocumentCategoryCreateSerializer,
        responses={201: DocumentCategorySerializer},
    )
    def post(self, request):
        serializer = DocumentCategoryCreateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        try:
            category = DocumentCategoryService(request.user).create_category(
                **serializer.validated_data
            )
        except DjangoValidationError as exc:
            return Response({"message": _error_message(exc)}, status=status.HTTP_400_BAD_REQUEST)
        except DjangoPermissionDenied as exc:
            raise PermissionDenied(str(exc)) from exc
        return Response(DocumentCategorySerializer(category).data, status=status.HTTP_201_CREATED)


class DocumentViewSet(mixins.ListModelMixin, mixins.CreateModelMixin, viewsets.GenericViewSet):
    serializer_class = DocumentRecordSerializer
    permission_classes = [IsAuthenticated]

    @extend_schema(
        parameters=[
            OpenApiParameter("q", str, OpenApiParameter.QUERY),
            OpenApiParameter("categoryId", int, OpenApiParameter.QUERY),
            OpenApiParameter("visibility", str, OpenApiParameter.QUERY),
        ],
        responses={200: DocumentRecordSerializer(many=True)},
    )
    def list(self, request, *args, **kwargs):
        return super().list(request, *args, **kwargs)

    def get_project(self):
        return get_object_or_404(ResearchProject.objects.all(), pk=self.kwargs["project_id"])

    def get_queryset(self):
        queryset = (
            DocumentRecord.objects.filter(
                project=self.get_project(),
                status=DocumentRecord.Status.ACTIVE,
            )
            .filter(visible_asset_q(self.request.user))
            .select_related("category", "document_file", "project")
            .distinct()
        )
        query = self.request.query_params.get("q")
        if query:
            queryset = queryset.filter(
                Q(title__icontains=query)
                | Q(description__icontains=query)
                | Q(category__name__icontains=query)
            )
        category_id = self.request.query_params.get("categoryId")
        if category_id:
            queryset = queryset.filter(category_id=category_id)
        visibility = self.request.query_params.get("visibility")
        if visibility:
            queryset = queryset.filter(visibility=visibility)
        return queryset

    def get_serializer_class(self):
        if self.action == "create":
            return DocumentUploadSerializer
        return DocumentRecordSerializer

    @extend_schema(
        request={"multipart/form-data": DocumentUploadSerializer},
        responses={201: DocumentRecordSerializer},
    )
    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        try:
            document = DocumentService(request.user, self.get_project()).upload_document(
                **serializer.validated_data
            )
        except DjangoValidationError as exc:
            return Response({"message": _error_message(exc)}, status=status.HTTP_400_BAD_REQUEST)
        except DjangoPermissionDenied as exc:
            raise PermissionDenied(str(exc)) from exc
        return Response(DocumentRecordSerializer(document).data, status=status.HTTP_201_CREATED)


class DocumentDownloadView(views.APIView):
    permission_classes = [IsAuthenticated]

    @extend_schema(
        responses={
            200: OpenApiResponse(description="Download descriptor"),
            403: OpenApiResponse(description="Download forbidden"),
        }
    )
    def get(self, request, document_id):
        document = get_object_or_404(
            DocumentRecord.objects.select_related("project", "document_file"),
            pk=document_id,
        )
        try:
            return Response(describe_document_download(request.user, document))
        except PermissionError as exc:
            raise PermissionDenied(str(exc)) from exc
