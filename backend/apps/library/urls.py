from django.urls import include, path
from rest_framework.routers import DefaultRouter

from .views import PaperDownloadView, PaperViewSet

router = DefaultRouter(trailing_slash=True)
router.register(r"projects/(?P<project_id>[^/.]+)/papers", PaperViewSet, basename="project-papers")

urlpatterns = [
    path("papers/<int:paper_id>/download", PaperDownloadView.as_view(), name="paper-download"),
    path("", include(router.urls)),
]
