from django.urls import include, path
from rest_framework.routers import DefaultRouter

from .views import ProjectTaskViewSet

router = DefaultRouter()
router.register("tasks", ProjectTaskViewSet, basename="project-tasks")

urlpatterns = [
    path("projects/<int:project_id>/", include(router.urls)),
]
