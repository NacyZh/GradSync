from django.core.exceptions import PermissionDenied as DjangoPermissionDenied
from django.core.exceptions import ValidationError as DjangoValidationError
from django.db.models import Q
from django.shortcuts import get_object_or_404
from rest_framework import mixins, status, views, viewsets
from rest_framework.decorators import action
from rest_framework.exceptions import PermissionDenied, ValidationError
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from apps.common.downloads import describe_code_artifact_download, describe_code_download
from apps.common.project_scope import visible_asset_q
from apps.projects.models import ResearchProject

from .models import CodeArtifact, CodeArtifactVersion
from .serializers import (
    CodeArtifactCreateSerializer,
    CodeArtifactSerializer,
    CodeArtifactUploadSerializer,
    CodeArtifactVersionCreateSerializer,
    CodeArtifactVersionSerializer,
)
from .services import CodeArtifactService


def _error_message(exc: DjangoValidationError) -> str:
    if hasattr(exc, "message_dict"):
        first_value = next(iter(exc.message_dict.values()))
        if isinstance(first_value, list):
            return str(first_value[0])
        return str(first_value)
    return str(exc.messages[0] if exc.messages else exc)


class CodeArtifactViewSet(mixins.ListModelMixin, mixins.CreateModelMixin, viewsets.GenericViewSet):
    permission_classes = [IsAuthenticated]

    def get_project(self):
        return get_object_or_404(ResearchProject.objects.all(), pk=self.kwargs["project_id"])

    def get_queryset(self):
        queryset = (
            CodeArtifact.objects.filter(project=self.get_project())
            .filter(visible_asset_q(self.request.user))
            .select_related("archive_file", "project")
            .prefetch_related("versions")
            .distinct()
        )
        query = self.request.query_params.get("q")
        if query:
            queryset = queryset.filter(
                Q(name__icontains=query)
                | Q(description__icontains=query)
                | Q(tags__icontains=query)
            )
        tag = self.request.query_params.get("tag")
        if tag:
            queryset = queryset.filter(tags__icontains=tag)
        visibility = self.request.query_params.get("visibility")
        if visibility:
            queryset = queryset.filter(visibility=visibility)
        return queryset

    def get_serializer_class(self):
        if self.action == "create":
            if "archive" in self.request.data:
                return CodeArtifactUploadSerializer
            return CodeArtifactCreateSerializer
        return CodeArtifactSerializer

    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        try:
            service = CodeArtifactService(request.user, self.get_project())
            if "upload" in serializer.validated_data:
                artifact = service.upload_archive(**serializer.validated_data)
            else:
                artifact = service.create_artifact(**serializer.validated_data)
        except DjangoValidationError as exc:
            message = _error_message(exc)
            status_code = (
                status.HTTP_409_CONFLICT
                if "checksum already exists" in message
                else status.HTTP_400_BAD_REQUEST
            )
            return Response({"message": message}, status=status_code)
        except (PermissionError, DjangoPermissionDenied) as exc:
            raise PermissionDenied(str(exc)) from exc
        return Response(CodeArtifactSerializer(artifact).data, status=status.HTTP_201_CREATED)

    @action(detail=True, methods=["post"], url_path="versions")
    def versions(self, request, project_id=None, pk=None):
        artifact = get_object_or_404(CodeArtifact, project=self.get_project(), pk=pk)
        serializer = CodeArtifactVersionCreateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        try:
            version = CodeArtifactService(request.user, self.get_project()).import_version(
                artifact, **serializer.validated_data
            )
        except DjangoValidationError as exc:
            return Response({"message": exc.messages[0]}, status=status.HTTP_409_CONFLICT)
        return Response(CodeArtifactVersionSerializer(version).data, status=status.HTTP_201_CREATED)

    @action(
        detail=True,
        methods=["post"],
        url_path=r"versions/(?P<version_id>[^/.]+)/download",
    )
    def download_version(self, request, project_id=None, pk=None, version_id=None):
        artifact = get_object_or_404(CodeArtifact, project=self.get_project(), pk=pk)
        version = get_object_or_404(CodeArtifactVersion, artifact=artifact, pk=version_id)
        try:
            return Response(describe_code_download(request.user, version))
        except PermissionError as exc:
            raise PermissionDenied(str(exc)) from exc


class CodeArtifactDownloadView(views.APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request, artifact_id):
        artifact = get_object_or_404(
            CodeArtifact.objects.select_related("project", "archive_file").prefetch_related("versions"),
            pk=artifact_id,
        )
        try:
            return Response(describe_code_artifact_download(request.user, artifact))
        except PermissionError as exc:
            raise PermissionDenied(str(exc)) from exc
