from django.urls import include, path
from rest_framework.routers import DefaultRouter

from .views import PaperViewSet

router = DefaultRouter(trailing_slash=True)
router.register(r"projects/(?P<project_id>[^/.]+)/papers", PaperViewSet, basename="project-papers")

urlpatterns = [path("", include(router.urls))]
