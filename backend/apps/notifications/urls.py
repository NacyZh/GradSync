from django.urls import include, path
from rest_framework.routers import DefaultRouter

from .views import ProjectNotificationViewSet

router = DefaultRouter()
router.register("notifications", ProjectNotificationViewSet, basename="project-notifications")

urlpatterns = [
    path("projects/<int:project_id>/", include(router.urls)),
]
