from django.core.exceptions import PermissionDenied as DjangoPermissionDenied
from django.core.exceptions import ValidationError as DjangoValidationError
from django.shortcuts import get_object_or_404
from drf_spectacular.utils import OpenApiResponse, extend_schema, extend_schema_view
from rest_framework import mixins, status, viewsets
from rest_framework.decorators import action
from rest_framework.exceptions import PermissionDenied, ValidationError
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from .models import ProjectMembership
from .serializers import (
    MembershipCreateSerializer,
    ProjectCreateSerializer,
    ProjectDashboardSerializer,
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
