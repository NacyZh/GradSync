from django.shortcuts import get_object_or_404
from django.utils import timezone
from drf_spectacular.utils import OpenApiResponse, extend_schema, extend_schema_view
from rest_framework import generics, mixins, status, views, viewsets
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from apps.projects.services import projects_visible_to

from .models import NotificationReadReceipt
from .serializers import NotificationReadSerializer, NotificationSerializer
from .services import notifications_visible_to


@extend_schema_view(
    get=extend_schema(
        responses={
            200: NotificationSerializer(many=True),
            401: OpenApiResponse(description="Authentication required"),
        }
    )
)
class NotificationStatusListView(generics.ListAPIView):
    serializer_class = NotificationSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        return notifications_visible_to(self.request.user)


class NotificationReadView(views.APIView):
    permission_classes = [IsAuthenticated]

    @extend_schema(
        request=NotificationReadSerializer,
        responses={200: OpenApiResponse(description="Visible notifications marked as read")},
    )
    def post(self, request):
        serializer = NotificationReadSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        through_id = serializer.validated_data["throughId"]
        notification_ids = list(
            notifications_visible_to(request.user)
            .filter(pk__lte=through_id)
            .values_list("pk", flat=True)
        )
        NotificationReadReceipt.objects.bulk_create(
            [
                NotificationReadReceipt(notification_id=notification_id, viewer=request.user)
                for notification_id in notification_ids
            ],
            ignore_conflicts=True,
        )
        return Response(
            {
                "throughId": through_id,
                "readAt": timezone.now(),
                "visibleCount": len(notification_ids),
            },
            status=status.HTTP_200_OK,
        )


class ProjectNotificationViewSet(mixins.ListModelMixin, viewsets.GenericViewSet):
    serializer_class = NotificationSerializer
    permission_classes = [IsAuthenticated]

    def get_project(self):
        return get_object_or_404(
            projects_visible_to(self.request.user), pk=self.kwargs["project_id"]
        )

    def get_queryset(self):
        return notifications_visible_to(self.request.user, project=self.get_project())
