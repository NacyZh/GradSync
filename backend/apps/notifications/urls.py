from django.urls import include, path
from rest_framework.routers import DefaultRouter

from .views import ProjectNotificationViewSet
from .views import NotificationStatusListView

router = DefaultRouter()
router.register("notifications", ProjectNotificationViewSet, basename="project-notifications")

urlpatterns = [
    path("notifications", NotificationStatusListView.as_view(), name="notification-status-list"),
    path("projects/<int:project_id>/", include(router.urls)),
]
