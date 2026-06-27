from django.urls import include, path
from rest_framework.routers import DefaultRouter

from .views import DraftViewSet, InlineCommentViewSet, WeeklyReportViewSet

router = DefaultRouter()
router.register("drafts", DraftViewSet, basename="project-drafts")
router.register("reports", WeeklyReportViewSet, basename="project-reports")
router.register("comments", InlineCommentViewSet, basename="project-comments")

urlpatterns = [
    path("projects/<int:project_id>/", include(router.urls)),
]
