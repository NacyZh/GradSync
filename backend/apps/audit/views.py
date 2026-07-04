from drf_spectacular.utils import OpenApiParameter, extend_schema
from rest_framework import generics
from rest_framework.permissions import IsAuthenticated

from apps.common.permissions import IsAdministrator

from .models import AuditEvent
from .serializers import AuditEventSerializer


class AuditEventListView(generics.ListAPIView):
    permission_classes = [IsAuthenticated, IsAdministrator]
    serializer_class = AuditEventSerializer

    @extend_schema(
        parameters=[
            OpenApiParameter("targetType", str, OpenApiParameter.QUERY),
            OpenApiParameter("actorId", int, OpenApiParameter.QUERY),
        ]
    )
    def get(self, request, *args, **kwargs):
        return super().get(request, *args, **kwargs)

    def get_queryset(self):
        queryset = AuditEvent.objects.select_related("actor", "project")
        target_type = self.request.query_params.get("targetType")
        actor_id = self.request.query_params.get("actorId")
        if target_type:
            queryset = queryset.filter(target_type=target_type)
        if actor_id:
            queryset = queryset.filter(actor_id=actor_id)
        return queryset
