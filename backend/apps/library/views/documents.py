from django.core.exceptions import PermissionDenied as DjangoPermissionDenied
from django.core.exceptions import ValidationError as DjangoValidationError
from django.db.models import Q
from django.shortcuts import get_object_or_404
from drf_spectacular.utils import OpenApiParameter, OpenApiResponse, extend_schema
from rest_framework import generics, mixins, status, views, viewsets
from rest_framework.exceptions import PermissionDenied
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from apps.projects.models import ResearchProject

from ..models import DocumentCategory, DocumentRecord
from ..serializers import (
    DocumentCategoryCreateSerializer,
    DocumentCategorySerializer,
    DocumentDeleteRequestSerializer,
    DocumentRecordSerializer,
    DocumentRenameRequestSerializer,
    DocumentUploadSerializer,
)
from ..services import (
    DocumentCategoryService,
    DocumentService,
    DownloadUnavailable,
    active_document_queryset,
    describe_document_download,
    shared_document_queryset_for,
)
from .papers import _error_message


def _is_document_conflict_message(message: str) -> bool:
    return any(
        conflict in message
        for conflict in [
            "already exists",
            "no longer active",
            "does not belong",
        ]
    )


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


class DocumentViewSet(
    mixins.ListModelMixin,
    mixins.RetrieveModelMixin,
    mixins.CreateModelMixin,
    viewsets.GenericViewSet,
):
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

    @extend_schema(
        responses={
            200: DocumentRecordSerializer,
            403: OpenApiResponse(description="Retrieve forbidden"),
            404: OpenApiResponse(description="Document not found"),
        },
    )
    def retrieve(self, request, *args, **kwargs):
        return super().retrieve(request, *args, **kwargs)

    def get_project(self):
        return get_object_or_404(ResearchProject.objects.all(), pk=self.kwargs["project_id"])

    def get_queryset(self):
        queryset = active_document_queryset(self.request.user, self.get_project())
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
        if self.action == "partial_update":
            return DocumentRenameRequestSerializer
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
        return Response(
            DocumentRecordSerializer(document, context=self.get_serializer_context()).data,
            status=status.HTTP_201_CREATED,
        )

    @extend_schema(
        request=DocumentRenameRequestSerializer,
        responses={
            200: DocumentRecordSerializer,
            400: OpenApiResponse(description="Rename validation failed"),
            403: OpenApiResponse(description="Rename forbidden"),
            404: OpenApiResponse(description="Document not found"),
            409: OpenApiResponse(description="Duplicate or unavailable document"),
        },
    )
    def partial_update(self, request, *args, **kwargs):
        document = get_object_or_404(
            DocumentRecord.objects.select_related("category", "document_file", "project"),
            project=self.get_project(),
            pk=kwargs["pk"],
        )
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        try:
            renamed = DocumentService(request.user, self.get_project()).rename_document(
                document,
                **serializer.validated_data,
            )
        except DjangoValidationError as exc:
            message = _error_message(exc)
            status_code = (
                status.HTTP_409_CONFLICT
                if _is_document_conflict_message(message)
                else status.HTTP_400_BAD_REQUEST
            )
            return Response({"message": message}, status=status_code)
        except DjangoPermissionDenied as exc:
            raise PermissionDenied(str(exc)) from exc
        return Response(
            DocumentRecordSerializer(renamed, context=self.get_serializer_context()).data,
            status=status.HTTP_200_OK,
        )

    @extend_schema(
        request=DocumentDeleteRequestSerializer,
        responses={
            204: OpenApiResponse(description="Document archived"),
            403: OpenApiResponse(description="Delete forbidden"),
            404: OpenApiResponse(description="Document not found"),
            409: OpenApiResponse(description="Unavailable document"),
        },
    )
    def destroy(self, request, *args, **kwargs):
        document = get_object_or_404(
            DocumentRecord.objects.select_related("category", "document_file", "project"),
            project=self.get_project(),
            pk=kwargs["pk"],
        )
        serializer = DocumentDeleteRequestSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        try:
            DocumentService(request.user, self.get_project()).archive_document(
                document,
                reason=serializer.validated_data.get("reason", ""),
            )
        except DjangoValidationError as exc:
            return Response({"message": _error_message(exc)}, status=status.HTTP_409_CONFLICT)
        except DjangoPermissionDenied as exc:
            raise PermissionDenied(str(exc)) from exc
        return Response(status=status.HTTP_204_NO_CONTENT)


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
        except DownloadUnavailable as exc:
            return Response({"message": str(exc)}, status=status.HTTP_410_GONE)
        except PermissionError as exc:
            raise PermissionDenied(str(exc)) from exc


class SharedDocumentListCreateView(generics.GenericAPIView):
    permission_classes = [IsAuthenticated]

    @extend_schema(
        parameters=[
            OpenApiParameter("q", str, OpenApiParameter.QUERY),
            OpenApiParameter("categoryId", int, OpenApiParameter.QUERY),
        ],
        responses={200: DocumentRecordSerializer(many=True)},
    )
    def get(self, request):
        queryset = shared_document_queryset_for(request.user)
        query = request.query_params.get("q")
        if query:
            queryset = queryset.filter(
                Q(title__icontains=query)
                | Q(description__icontains=query)
                | Q(category__name__icontains=query)
            )
        category_id = request.query_params.get("categoryId")
        if category_id:
            queryset = queryset.filter(category_id=category_id)
        page = self.paginate_queryset(queryset)
        if page is not None:
            serializer = DocumentRecordSerializer(page, many=True, context={"request": request})
            return self.get_paginated_response(serializer.data)
        serializer = DocumentRecordSerializer(
            queryset, many=True, context={"request": request}
        )
        return Response(serializer.data)

    @extend_schema(
        request={"multipart/form-data": DocumentUploadSerializer},
        responses={201: DocumentRecordSerializer},
    )
    def post(self, request):
        serializer = DocumentUploadSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        validated = dict(serializer.validated_data)
        validated.pop("visibility", None)
        try:
            document = DocumentService(request.user, None).upload_standalone_document(
                **validated
            )
        except DjangoValidationError as exc:
            return Response({"message": _error_message(exc)}, status=status.HTTP_400_BAD_REQUEST)
        except DjangoPermissionDenied as exc:
            raise PermissionDenied(str(exc)) from exc
        return Response(
            DocumentRecordSerializer(document, context={"request": request}).data,
            status=status.HTTP_201_CREATED,
        )


class SharedDocumentDetailView(views.APIView):
    permission_classes = [IsAuthenticated]

    @extend_schema(responses={200: DocumentRecordSerializer})
    def get(self, request, document_id):
        document = get_object_or_404(shared_document_queryset_for(request.user), pk=document_id)
        return Response(DocumentRecordSerializer(document, context={"request": request}).data)


class SharedDocumentDownloadView(views.APIView):
    permission_classes = [IsAuthenticated]

    @extend_schema(responses={200: OpenApiResponse(description="Download descriptor")})
    def get(self, request, document_id):
        document = get_object_or_404(shared_document_queryset_for(request.user), pk=document_id)
        try:
            return Response(describe_document_download(request.user, document))
        except DownloadUnavailable as exc:
            return Response({"message": str(exc)}, status=status.HTTP_410_GONE)
        except PermissionError as exc:
            raise PermissionDenied(str(exc)) from exc
