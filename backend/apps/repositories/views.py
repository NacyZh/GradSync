from django.core.exceptions import PermissionDenied as DjangoPermissionDenied
from django.core.exceptions import ValidationError as DjangoValidationError
from django.db.models import Q
from django.shortcuts import get_object_or_404
from drf_spectacular.utils import OpenApiParameter, OpenApiResponse, extend_schema
from rest_framework import generics, mixins, status, views, viewsets
from rest_framework.decorators import action
from rest_framework.exceptions import PermissionDenied
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from apps.common.project_scope import visible_asset_q
from apps.projects.models import ResearchProject

from .download_services import describe_code_artifact_download, describe_code_download
from .models import CodeArtifact, CodeArtifactVersion
from .serializers import (
    CodeArtifactCreateSerializer,
    CodeArtifactRenameSerializer,
    CodeArtifactSerializer,
    CodeArtifactUploadSerializer,
    CodeArtifactVersionCreateSerializer,
    CodeArtifactVersionSerializer,
    CodeUploadPolicySerializer,
)
from .services import (
    CodeArtifactService,
    delete_shared_code_artifact,
    rename_shared_code_artifact,
    shared_code_artifact_queryset_for,
)
from .upload_policy import code_archive_upload_policy


def _error_message(exc: DjangoValidationError) -> str:
    if hasattr(exc, "message_dict"):
        first_value = next(iter(exc.message_dict.values()))
        if isinstance(first_value, list):
            return str(first_value[0])
        return str(first_value)
    return str(exc.messages[0] if exc.messages else exc)


def _is_conflict_message(message: str) -> bool:
    return any(
        conflict in message
        for conflict in [
            "already exists",
            "no longer active",
            "does not belong",
        ]
    )


class CodeArtifactViewSet(
    mixins.ListModelMixin,
    mixins.RetrieveModelMixin,
    mixins.CreateModelMixin,
    viewsets.GenericViewSet,
):
    permission_classes = [IsAuthenticated]

    @extend_schema(
        parameters=[
            OpenApiParameter("q", str, OpenApiParameter.QUERY),
            OpenApiParameter("tag", str, OpenApiParameter.QUERY),
            OpenApiParameter("visibility", str, OpenApiParameter.QUERY),
        ],
        responses={
            200: CodeArtifactSerializer(many=True),
            401: OpenApiResponse(description="Authentication required"),
        },
    )
    def list(self, request, *args, **kwargs):
        return super().list(request, *args, **kwargs)

    @extend_schema(
        responses={
            200: CodeArtifactSerializer,
            403: OpenApiResponse(description="Retrieve forbidden"),
            404: OpenApiResponse(description="Code artifact not found"),
        },
    )
    def retrieve(self, request, *args, **kwargs):
        return super().retrieve(request, *args, **kwargs)

    def get_project(self):
        return get_object_or_404(ResearchProject.objects.all(), pk=self.kwargs["project_id"])

    def get_queryset(self):
        queryset = (
            CodeArtifact.objects.filter(project=self.get_project())
            .filter(status=CodeArtifact.Status.ACTIVE)
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
        if self.action == "partial_update":
            return CodeArtifactRenameSerializer
        return CodeArtifactSerializer

    @extend_schema(
        request={
            "application/json": CodeArtifactCreateSerializer,
            "multipart/form-data": CodeArtifactUploadSerializer,
        },
        responses={
            201: CodeArtifactSerializer,
            400: OpenApiResponse(description="Code artifact validation failed"),
            403: OpenApiResponse(description="Code artifact creation forbidden"),
            409: OpenApiResponse(description="Duplicate code artifact"),
        },
    )
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
        return Response(
            CodeArtifactSerializer(artifact, context=self.get_serializer_context()).data,
            status=status.HTTP_201_CREATED,
        )

    @extend_schema(
        request=CodeArtifactRenameSerializer,
        responses={
            200: CodeArtifactSerializer,
            400: OpenApiResponse(description="Rename validation failed"),
            403: OpenApiResponse(description="Rename forbidden"),
            404: OpenApiResponse(description="Code artifact not found"),
            409: OpenApiResponse(description="Duplicate or unavailable code artifact"),
        },
    )
    def partial_update(self, request, *args, **kwargs):
        artifact = get_object_or_404(
            CodeArtifact.objects.select_related("archive_file", "project").prefetch_related(
                "versions"
            ),
            project=self.get_project(),
            pk=kwargs["pk"],
        )
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        try:
            renamed = CodeArtifactService(request.user, self.get_project()).rename_artifact(
                artifact,
                **serializer.validated_data,
            )
        except DjangoValidationError as exc:
            message = _error_message(exc)
            status_code = (
                status.HTTP_409_CONFLICT
                if _is_conflict_message(message)
                else status.HTTP_400_BAD_REQUEST
            )
            return Response({"message": message}, status=status_code)
        except (PermissionError, DjangoPermissionDenied) as exc:
            raise PermissionDenied(str(exc)) from exc
        return Response(
            CodeArtifactSerializer(renamed, context=self.get_serializer_context()).data,
            status=status.HTTP_200_OK,
        )

    @extend_schema(
        responses={
            204: OpenApiResponse(description="Code artifact archived"),
            403: OpenApiResponse(description="Delete forbidden"),
            404: OpenApiResponse(description="Code artifact not found"),
            409: OpenApiResponse(description="Unavailable code artifact"),
        },
    )
    def destroy(self, request, *args, **kwargs):
        artifact = get_object_or_404(
            CodeArtifact.objects.select_related("archive_file", "project").prefetch_related(
                "versions"
            ),
            project=self.get_project(),
            pk=kwargs["pk"],
        )
        try:
            CodeArtifactService(request.user, self.get_project()).archive_artifact(artifact)
        except DjangoValidationError as exc:
            return Response({"message": _error_message(exc)}, status=status.HTTP_409_CONFLICT)
        except (PermissionError, DjangoPermissionDenied) as exc:
            raise PermissionDenied(str(exc)) from exc
        return Response(status=status.HTTP_204_NO_CONTENT)

    @extend_schema(
        request=CodeArtifactVersionCreateSerializer,
        responses={
            201: CodeArtifactVersionSerializer,
            400: OpenApiResponse(description="Code version validation failed"),
            403: OpenApiResponse(description="Code version import forbidden"),
            409: OpenApiResponse(description="Duplicate code version"),
        },
    )
    @action(detail=True, methods=["post"], url_path="versions")
    def versions(self, request, project_id=None, pk=None):
        artifact = get_object_or_404(
            CodeArtifact,
            project=self.get_project(),
            pk=pk,
            status=CodeArtifact.Status.ACTIVE,
        )
        serializer = CodeArtifactVersionCreateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        try:
            version = CodeArtifactService(request.user, self.get_project()).import_version(
                artifact, **serializer.validated_data
            )
        except DjangoValidationError as exc:
            return Response({"message": exc.messages[0]}, status=status.HTTP_409_CONFLICT)
        return Response(CodeArtifactVersionSerializer(version).data, status=status.HTTP_201_CREATED)

    @extend_schema(
        responses={
            200: OpenApiResponse(description="Download descriptor"),
            403: OpenApiResponse(description="Download forbidden"),
            404: OpenApiResponse(description="Code artifact version not found"),
        }
    )
    @action(
        detail=True,
        methods=["post"],
        url_path=r"versions/(?P<version_id>[^/.]+)/download",
    )
    def download_version(self, request, project_id=None, pk=None, version_id=None):
        artifact = get_object_or_404(
            CodeArtifact,
            project=self.get_project(),
            pk=pk,
            status=CodeArtifact.Status.ACTIVE,
        )
        version = get_object_or_404(
            CodeArtifactVersion,
            artifact=artifact,
            pk=version_id,
            status=CodeArtifactVersion.Status.ACTIVE,
        )
        try:
            return Response(describe_code_download(request.user, version))
        except PermissionError as exc:
            raise PermissionDenied(str(exc)) from exc


class CodeArtifactDownloadView(views.APIView):
    permission_classes = [IsAuthenticated]

    @extend_schema(
        responses={
            200: OpenApiResponse(description="Download descriptor"),
            403: OpenApiResponse(description="Download forbidden"),
            404: OpenApiResponse(description="Code artifact not found"),
        }
    )
    def get(self, request, artifact_id):
        artifact = get_object_or_404(
            CodeArtifact.objects.select_related("project", "archive_file").prefetch_related(
                "versions"
            ),
            pk=artifact_id,
            status=CodeArtifact.Status.ACTIVE,
        )
        try:
            return Response(describe_code_artifact_download(request.user, artifact))
        except PermissionError as exc:
            raise PermissionDenied(str(exc)) from exc


class CodeArtifactUploadPolicyView(views.APIView):
    permission_classes = [IsAuthenticated]

    @extend_schema(
        responses={
            200: CodeUploadPolicySerializer,
            401: OpenApiResponse(description="Authentication required"),
        }
    )
    def get(self, request):
        return Response(CodeUploadPolicySerializer(code_archive_upload_policy()).data)


class SharedCodeArtifactListCreateView(generics.GenericAPIView):
    permission_classes = [IsAuthenticated]

    @extend_schema(
        parameters=[
            OpenApiParameter("q", str, OpenApiParameter.QUERY),
            OpenApiParameter("tag", str, OpenApiParameter.QUERY),
        ],
        responses={200: CodeArtifactSerializer(many=True)},
    )
    def get(self, request):
        queryset = shared_code_artifact_queryset_for(request.user)
        query = request.query_params.get("q")
        if query:
            queryset = queryset.filter(
                Q(name__icontains=query)
                | Q(description__icontains=query)
                | Q(tags__icontains=query)
            )
        tag = request.query_params.get("tag")
        if tag:
            queryset = queryset.filter(tags__icontains=tag)
        page = self.paginate_queryset(queryset)
        if page is not None:
            serializer = CodeArtifactSerializer(
                page,
                many=True,
                context={"request": request, "shared_section": True},
            )
            return self.get_paginated_response(serializer.data)
        serializer = CodeArtifactSerializer(
            queryset,
            many=True,
            context={"request": request, "shared_section": True},
        )
        return Response(serializer.data)

    @extend_schema(
        request={
            "application/json": CodeArtifactCreateSerializer,
            "multipart/form-data": CodeArtifactUploadSerializer,
        },
        responses={201: CodeArtifactSerializer},
    )
    def post(self, request):
        serializer_class = (
            CodeArtifactUploadSerializer
            if "archive" in request.data
            else CodeArtifactCreateSerializer
        )
        serializer = serializer_class(data=request.data)
        serializer.is_valid(raise_exception=True)
        validated = dict(serializer.validated_data)
        validated.pop("visibility", None)
        try:
            service = CodeArtifactService(request.user, None)
            if "upload" in validated:
                artifact = service.upload_standalone_archive(**validated)
            else:
                artifact = service.create_standalone_artifact(**validated)
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
        return Response(
            CodeArtifactSerializer(
                artifact,
                context={"request": request, "shared_section": True},
            ).data,
            status=status.HTTP_201_CREATED,
        )


class SharedCodeArtifactDetailView(views.APIView):
    permission_classes = [IsAuthenticated]

    @extend_schema(responses={200: CodeArtifactSerializer})
    def get(self, request, artifact_id):
        artifact = get_object_or_404(
            shared_code_artifact_queryset_for(request.user), pk=artifact_id
        )
        return Response(
            CodeArtifactSerializer(
                artifact,
                context={"request": request, "shared_section": True},
            ).data
        )

    @extend_schema(
        request=CodeArtifactRenameSerializer,
        responses={
            200: CodeArtifactSerializer,
            400: OpenApiResponse(description="Rename validation failed"),
            403: OpenApiResponse(description="Rename forbidden"),
            404: OpenApiResponse(description="Code artifact not found"),
            409: OpenApiResponse(description="Duplicate or unavailable code artifact"),
        },
    )
    def patch(self, request, artifact_id):
        artifact = get_object_or_404(
            shared_code_artifact_queryset_for(request.user), pk=artifact_id
        )
        serializer = CodeArtifactRenameSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        try:
            renamed = rename_shared_code_artifact(
                actor=request.user,
                artifact=artifact,
                **serializer.validated_data,
            )
        except DjangoValidationError as exc:
            message = _error_message(exc)
            status_code = (
                status.HTTP_409_CONFLICT
                if _is_conflict_message(message) or "already exists" in message
                else status.HTTP_400_BAD_REQUEST
            )
            return Response({"message": message}, status=status_code)
        except (PermissionError, DjangoPermissionDenied) as exc:
            raise PermissionDenied(str(exc)) from exc
        return Response(
            CodeArtifactSerializer(
                renamed,
                context={"request": request, "shared_section": True},
            ).data,
            status=status.HTTP_200_OK,
        )

    @extend_schema(
        responses={
            204: OpenApiResponse(description="Code artifact archived"),
            403: OpenApiResponse(description="Delete forbidden"),
            404: OpenApiResponse(description="Code artifact not found"),
            409: OpenApiResponse(description="Unavailable code artifact"),
        },
    )
    def delete(self, request, artifact_id):
        artifact = get_object_or_404(
            CodeArtifact.objects.select_related("archive_file", "project", "source_project")
            .prefetch_related("versions"),
            pk=artifact_id,
        )
        try:
            delete_shared_code_artifact(
                actor=request.user,
                artifact=artifact,
                reason=str(request.data.get("reason", "")) if hasattr(request, "data") else "",
            )
        except DjangoValidationError as exc:
            return Response({"message": _error_message(exc)}, status=status.HTTP_409_CONFLICT)
        except (PermissionError, DjangoPermissionDenied) as exc:
            raise PermissionDenied(str(exc)) from exc
        return Response(status=status.HTTP_204_NO_CONTENT)


class SharedCodeArtifactDownloadView(views.APIView):
    permission_classes = [IsAuthenticated]

    @extend_schema(responses={200: OpenApiResponse(description="Download descriptor")})
    def get(self, request, artifact_id):
        artifact = get_object_or_404(
            shared_code_artifact_queryset_for(request.user), pk=artifact_id
        )
        try:
            return Response(describe_code_artifact_download(request.user, artifact))
        except PermissionError as exc:
            raise PermissionDenied(str(exc)) from exc
