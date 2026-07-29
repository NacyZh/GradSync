from drf_spectacular.utils import OpenApiResponse, extend_schema
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.common.permissions import IsAdministrator

from .serializers import ProjectHealthSnapshotSerializer
from .services import build_project_health_snapshot


class ProjectHealthSnapshotView(APIView):
    permission_classes = [IsAuthenticated, IsAdministrator]

    @extend_schema(
        responses={
            200: ProjectHealthSnapshotSerializer,
            401: OpenApiResponse(description="Authentication required"),
            403: OpenApiResponse(description="Administrator access required"),
        }
    )
    def get(self, request):
        return Response(ProjectHealthSnapshotSerializer(build_project_health_snapshot()).data)
