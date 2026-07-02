from django.core.exceptions import ValidationError as DjangoValidationError
from django.db.models import Q
from django.shortcuts import get_object_or_404
from rest_framework import mixins, status, viewsets
from rest_framework.decorators import action
from rest_framework.exceptions import PermissionDenied, ValidationError
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from apps.common.downloads import describe_code_download
from apps.projects.services import projects_visible_to

from .models import CodeArtifact, CodeArtifactVersion
from .serializers import (
    CodeArtifactCreateSerializer,
    CodeArtifactSerializer,
    CodeArtifactVersionCreateSerializer,
    CodeArtifactVersionSerializer,
)
from .services import CodeArtifactService


class CodeArtifactViewSet(mixins.ListModelMixin, mixins.CreateModelMixin, viewsets.GenericViewSet):
    permission_classes = [IsAuthenticated]

    def get_project(self):
        return get_object_or_404(projects_visible_to(self.request.user), pk=self.kwargs["project_id"])

    def get_queryset(self):
        queryset = CodeArtifact.objects.filter(project=self.get_project()).prefetch_related("versions")
        query = self.request.query_params.get("q")
        if query:
            queryset = queryset.filter(
                Q(name__icontains=query) | Q(description__icontains=query) | Q(tags__icontains=query)
            )
        tag = self.request.query_params.get("tag")
        if tag:
            queryset = queryset.filter(tags__icontains=tag)
        return queryset

    def get_serializer_class(self):
        if self.action == "create":
            return CodeArtifactCreateSerializer
        return CodeArtifactSerializer

    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        try:
            artifact = CodeArtifactService(request.user, self.get_project()).create_artifact(
                **serializer.validated_data
            )
        except DjangoValidationError as exc:
            raise ValidationError(exc.messages) from exc
        return Response(CodeArtifactSerializer(artifact).data, status=status.HTTP_201_CREATED)

    @action(detail=True, methods=["post"], url_path="versions")
    def versions(self, request, project_id=None, pk=None):
        artifact = get_object_or_404(CodeArtifact, project=self.get_project(), pk=pk)
        serializer = CodeArtifactVersionCreateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        try:
            version = CodeArtifactService(request.user, self.get_project()).upload_version(
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
