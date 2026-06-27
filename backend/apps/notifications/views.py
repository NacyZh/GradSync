from django.shortcuts import get_object_or_404
from rest_framework import mixins, viewsets
from rest_framework.permissions import IsAuthenticated

from apps.projects.services import projects_visible_to

from .models import Notification
from .serializers import NotificationSerializer


class ProjectNotificationViewSet(mixins.ListModelMixin, viewsets.GenericViewSet):
    serializer_class = NotificationSerializer
    permission_classes = [IsAuthenticated]

    def get_project(self):
        return get_object_or_404(
            projects_visible_to(self.request.user), pk=self.kwargs["project_id"]
        )

    def get_queryset(self):
        return Notification.objects.filter(project=self.get_project(), recipient=self.request.user)
