from django.urls import include, path
from rest_framework.routers import DefaultRouter

from .views import (
    DocumentCategoryView,
    DocumentDownloadView,
    DocumentViewSet,
    PaperDownloadView,
    PaperImportReviewView,
    PaperImportStatusView,
    PaperViewSet,
    SharedPaperDetailView,
    SharedPaperDownloadView,
    SharedPaperListCreateView,
    SharedPaperUploadPolicyView,
)

router = DefaultRouter(trailing_slash=True)
router.register(r"projects/(?P<project_id>[^/.]+)/papers", PaperViewSet, basename="project-papers")
router.register(
    r"projects/(?P<project_id>[^/.]+)/documents",
    DocumentViewSet,
    basename="project-documents",
)

urlpatterns = [
    path("document-categories", DocumentCategoryView.as_view(), name="document-categories"),
    path("document-categories/", DocumentCategoryView.as_view(), name="document-categories-slash"),
    path(
        "documents/<int:document_id>/download",
        DocumentDownloadView.as_view(),
        name="document-download",
    ),
    path(
        "projects/<int:project_id>/documents",
        DocumentViewSet.as_view({"get": "list", "post": "create"}),
        name="project-documents-noslash",
    ),
    path("papers/<int:paper_id>/download", PaperDownloadView.as_view(), name="paper-download"),
    path("library/papers/", SharedPaperListCreateView.as_view(), name="shared-paper-list"),
    path(
        "library/papers/upload-policy/",
        SharedPaperUploadPolicyView.as_view(),
        name="shared-paper-upload-policy",
    ),
    path(
        "library/papers/<int:paper_id>/",
        SharedPaperDetailView.as_view(),
        name="shared-paper-detail",
    ),
    path(
        "library/papers/<int:paper_id>/download/",
        SharedPaperDownloadView.as_view(),
        name="shared-paper-download",
    ),
    path(
        "library/paper-imports/<int:import_job_id>/",
        PaperImportStatusView.as_view(),
        name="paper-import-status",
    ),
    path(
        "library/paper-imports/<int:import_job_id>/review/",
        PaperImportReviewView.as_view(),
        name="paper-import-review",
    ),
    path("", include(router.urls)),
]
