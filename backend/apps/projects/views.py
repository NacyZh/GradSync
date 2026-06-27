from rest_framework import mixins, status, viewsets
from rest_framework.decorators import action
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from .models import ProjectMembership
from .serializers import (
    ProjectCreateSerializer,
    ProjectDashboardSerializer,
    ProjectMembershipSerializer,
    ProjectSerializer,
    ProjectUpdateSerializer,
)
from .services import ProjectService, projects_visible_to


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

    @action(detail=True, methods=["post"], url_path="members")
    def add_member(self, request, pk=None):
        project = self.get_object()
        membership = ProjectService(request.user).add_member(
            project, user_id=request.data["user_id"], role=request.data["role"]
        )
        return Response(
            ProjectMembershipSerializer(membership).data, status=status.HTTP_201_CREATED
        )

    @action(detail=True, methods=["post"], url_path="members/(?P<membership_id>[^/.]+)/remove")
    def remove_member(self, request, pk=None, membership_id=None):
        project = self.get_object()
        membership = ProjectMembership.objects.get(project=project, pk=membership_id)
        membership = ProjectService(request.user).remove_member(membership)
        return Response(ProjectMembershipSerializer(membership).data)

    @action(detail=True, methods=["post"])
    def archive(self, request, pk=None):
        project = ProjectService(request.user).archive_project(self.get_object())
        return Response(ProjectSerializer(project).data)

    @action(detail=True, methods=["post"])
    def reopen(self, request, pk=None):
        project = ProjectService(request.user).reopen_project(self.get_object())
        return Response(ProjectSerializer(project).data)
