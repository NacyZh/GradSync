import re

from django.core.exceptions import PermissionDenied as DjangoPermissionDenied
from django.core.exceptions import ValidationError as DjangoValidationError
from django.shortcuts import get_object_or_404
from drf_spectacular.utils import OpenApiResponse, extend_schema, extend_schema_view
from rest_framework import mixins, status, views, viewsets
from rest_framework.decorators import action
from rest_framework.exceptions import PermissionDenied, ValidationError
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from .legacy_link_services import resolve_legacy_project_link
from .material_services import (
    change_project_material_visibility,
    create_project_material,
    project_material_queryset_for,
)
from .models import ProjectMaterial, ProjectMembership, ResearchProject
from .serializers import (
    MembershipCreateSerializer,
    ProjectCreateSerializer,
    ProjectDashboardSerializer,
    ProjectMaterialCreateSerializer,
    ProjectMaterialSerializer,
    ProjectMaterialVisibilitySerializer,
    ProjectMembershipSerializer,
    ProjectSerializer,
    ProjectUpdateSerializer,
)
from .services import ProjectService, projects_visible_to


@extend_schema_view(
    retrieve=extend_schema(
        responses={
            200: ProjectDashboardSerializer,
            403: OpenApiResponse(description="Project access forbidden"),
        }
    )
)
class ProjectViewSet(
    mixins.CreateModelMixin,
    mixins.ListModelMixin,
    mixins.RetrieveModelMixin,
    mixins.UpdateModelMixin,
    viewsets.GenericViewSet,
):
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        return projects_visible_to(self.request.user).prefetch_related("memberships")

    def get_serializer_class(self):
        if self.action == "create":
            return ProjectCreateSerializer
        if self.action in {"update", "partial_update"}:
            return ProjectUpdateSerializer
        if self.action == "retrieve":
            return ProjectDashboardSerializer
        return ProjectSerializer

    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        project = serializer.save()
        return Response(ProjectSerializer(project).data, status=status.HTTP_201_CREATED)

    def perform_update(self, serializer):
        project = ProjectService(self.request.user).update_project(
            self.get_object(), **serializer.validated_data
        )
        serializer.instance = project

    @extend_schema(
        methods=["POST"],
        request=MembershipCreateSerializer,
        responses={
            201: ProjectMembershipSerializer,
            403: OpenApiResponse(description="Membership change forbidden"),
        },
    )
    @extend_schema(methods=["GET"], responses={200: ProjectMembershipSerializer(many=True)})
    @action(detail=True, methods=["get", "post"], url_path="members")
    def members(self, request, pk=None):
        if request.method == "GET":
            project = self.get_object()
            memberships = project.memberships.select_related("user").order_by(
                "status", "role", "user__email"
            )
            return Response(ProjectMembershipSerializer(memberships, many=True).data)

        project = self.get_object()
        if "studentId" in request.data:
            serializer = MembershipCreateSerializer(data=request.data)
            serializer.is_valid(raise_exception=True)
            try:
                membership = ProjectService(request.user).add_student_member(
                    project, student_id=serializer.validated_data["studentId"]
                )
            except DjangoPermissionDenied as exc:
                raise PermissionDenied(str(exc)) from exc
            except DjangoValidationError as exc:
                raise ValidationError({"message": exc.messages[0]}) from exc
        else:
            membership = ProjectService(request.user).add_member(
                project, user_id=request.data["user_id"], role=request.data["role"]
            )
        return Response(
            ProjectMembershipSerializer(membership).data, status=status.HTTP_201_CREATED
        )

    @action(detail=True, methods=["post"], url_path="members/(?P<membership_id>[^/.]+)/remove")
    def remove_member(self, request, pk=None, membership_id=None):
        project = self.get_object()
        membership = get_object_or_404(ProjectMembership, project=project, pk=membership_id)
        try:
            membership = ProjectService(request.user).remove_member(membership)
        except DjangoPermissionDenied as exc:
            raise PermissionDenied(str(exc)) from exc
        except DjangoValidationError as exc:
            raise ValidationError({"message": exc.messages[0]}) from exc
        return Response(ProjectMembershipSerializer(membership).data)

    @action(detail=True, methods=["delete"], url_path="members/(?P<membership_id>[^/.]+)")
    def delete_member(self, request, pk=None, membership_id=None):
        project = self.get_object()
        membership = get_object_or_404(ProjectMembership, project=project, pk=membership_id)
        try:
            ProjectService(request.user).remove_member(membership)
        except DjangoPermissionDenied as exc:
            raise PermissionDenied(str(exc)) from exc
        except DjangoValidationError as exc:
            raise ValidationError({"message": exc.messages[0]}) from exc
        return Response(status=status.HTTP_204_NO_CONTENT)

    @action(detail=True, methods=["post"])
    def archive(self, request, pk=None):
        project = ProjectService(request.user).archive_project(self.get_object())
        return Response(ProjectSerializer(project).data)

    @action(detail=True, methods=["post"])
    def reopen(self, request, pk=None):
        project = ProjectService(request.user).reopen_project(self.get_object())
        return Response(ProjectSerializer(project).data)

    @extend_schema(
        methods=["GET"],
        responses={200: ProjectMaterialSerializer(many=True)},
    )
    @extend_schema(
        methods=["POST"],
        request={"multipart/form-data": ProjectMaterialCreateSerializer},
        responses={201: ProjectMaterialSerializer},
    )
    @action(detail=True, methods=["get", "post"], url_path="materials")
    def materials(self, request, pk=None):
        project = self.get_object()
        if request.method == "GET":
            queryset = project_material_queryset_for(request.user, project)
            material_type = request.query_params.get("type")
            visibility = request.query_params.get("visibility")
            query = request.query_params.get("q") or request.query_params.get("search")
            if material_type:
                queryset = queryset.filter(material_type=material_type)
            if visibility:
                queryset = queryset.filter(visibility_state=visibility)
            if query:
                matching_ids = [
                    material.id
                    for material in queryset
                    if query.casefold()
                    in ProjectMaterialSerializer(
                        material, context={"request": request}
                    ).data.get("displayName", "").casefold()
                ]
                queryset = queryset.filter(id__in=matching_ids)
            return Response(
                {
                    "count": queryset.count(),
                    "results": ProjectMaterialSerializer(
                        queryset, many=True, context={"request": request}
                    ).data,
                }
            )

        serializer = ProjectMaterialCreateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        try:
            material = create_project_material(
                user=request.user,
                project=project,
                **serializer.validated_data,
            )
        except DjangoPermissionDenied as exc:
            raise PermissionDenied(str(exc)) from exc
        except DjangoValidationError as exc:
            raise ValidationError({"message": exc.messages[0]}) from exc
        return Response(
            ProjectMaterialSerializer(material, context={"request": request}).data,
            status=status.HTTP_201_CREATED,
        )

    @extend_schema(
        request=ProjectMaterialVisibilitySerializer,
        responses={
            200: ProjectMaterialSerializer,
            403: OpenApiResponse(description="Visibility change forbidden"),
        },
    )
    @action(
        detail=True,
        methods=["patch"],
        url_path="materials/(?P<material_id>[^/.]+)/visibility",
    )
    def material_visibility(self, request, pk=None, material_id=None):
        project = self.get_object()
        material = get_object_or_404(ProjectMaterial, source_project=project, pk=material_id)
        serializer = ProjectMaterialVisibilitySerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        try:
            material = change_project_material_visibility(
                user=request.user,
                material=material,
                **serializer.validated_data,
            )
        except DjangoPermissionDenied as exc:
            raise PermissionDenied(str(exc)) from exc
        except DjangoValidationError as exc:
            raise ValidationError({"message": exc.messages[0]}) from exc
        return Response(ProjectMaterialSerializer(material, context={"request": request}).data)


class LegacyBoundaryLinkView(views.APIView):
    permission_classes = [IsAuthenticated]

    @extend_schema(
        request={
            "application/json": {
                "type": "object",
                "properties": {"path": {"type": "string"}},
            }
        },
        responses={200: OpenApiResponse(description="Legacy boundary resolution")},
    )
    def post(self, request):
        path_value = str(request.data.get("path", ""))
        match = re.fullmatch(
            r"/projects/(?P<project_id>\d+)/(?P<section>papers|code|documents|writing)/?",
            path_value,
        )
        if not match:
            return Response(
                {
                    "mode": "guidance",
                    "targetPath": "",
                    "message": "This link no longer maps to a shared workspace section.",
                },
                status=status.HTTP_404_NOT_FOUND,
            )
        project = get_object_or_404(ResearchProject, pk=match.group("project_id"))
        resolution = resolve_legacy_project_link(
            user=request.user,
            project=project,
            section=match.group("section"),
        )
        return Response(
            {
                "mode": "denied" if resolution.outcome == "denied" else resolution.outcome,
                "targetPath": resolution.target_url,
                "message": resolution.message,
            },
            status=resolution.status_code,
        )
