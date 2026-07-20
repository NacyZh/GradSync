from django.urls import include, path
from rest_framework.routers import DefaultRouter

from .views import NotificationReadView, NotificationStatusListView, ProjectNotificationViewSet

router = DefaultRouter()
router.register("notifications", ProjectNotificationViewSet, basename="project-notifications")

urlpatterns = [
    path("notifications/read", NotificationReadView.as_view(), name="notification-read"),
    path("notifications", NotificationStatusListView.as_view(), name="notification-status-list"),
    path("projects/<int:project_id>/", include(router.urls)),
]
