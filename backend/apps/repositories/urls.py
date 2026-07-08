from django.urls import include, path
from rest_framework.routers import DefaultRouter

from .views import CodeArtifactDownloadView, CodeArtifactUploadPolicyView, CodeArtifactViewSet

router = DefaultRouter(trailing_slash=True)
router.register(
    r"projects/(?P<project_id>[^/.]+)/code-artifacts",
    CodeArtifactViewSet,
    basename="project-code-artifacts",
)

urlpatterns = [
    path(
        "code-artifacts/upload-policy/",
        CodeArtifactUploadPolicyView.as_view(),
        name="code-artifact-upload-policy",
    ),
    path(
        "code-artifacts/<int:artifact_id>/download",
        CodeArtifactDownloadView.as_view(),
        name="code-artifact-download",
    ),
    path("", include(router.urls)),
]
