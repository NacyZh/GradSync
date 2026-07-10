from django.urls import path
from rest_framework.routers import DefaultRouter

from .views import LegacyBoundaryLinkView, ProjectViewSet

router = DefaultRouter()
router.register("projects", ProjectViewSet, basename="projects")

urlpatterns = [
    path("boundary/legacy-link/", LegacyBoundaryLinkView.as_view(), name="legacy-boundary-link"),
    *router.urls,
]
