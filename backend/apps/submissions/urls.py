from django.urls import include, path
from rest_framework.routers import DefaultRouter

from .views import (
    DraftViewSet,
    InlineCommentViewSet,
    TeacherFeedbackDownloadView,
    TeacherFeedbackSubmitView,
    WeeklyReportViewSet,
    WritingProjectViewSet,
    WritingVersionUploadView,
)

router = DefaultRouter()
router.register("drafts", DraftViewSet, basename="project-drafts")
router.register("reports", WeeklyReportViewSet, basename="project-reports")
router.register("comments", InlineCommentViewSet, basename="project-comments")
router.register("writing-projects", WritingProjectViewSet, basename="project-writing")

urlpatterns = [
    path("projects/<int:project_id>/", include(router.urls)),
    path(
        "writing-projects/<int:writing_project_id>/versions",
        WritingVersionUploadView.as_view(),
        name="writing-version-upload",
    ),
    path(
        "writing-projects/<int:writing_project_id>/versions/",
        WritingVersionUploadView.as_view(),
        name="writing-version-upload-slash",
    ),
    path(
        "writing-versions/<int:writing_version_id>/feedback",
        TeacherFeedbackSubmitView.as_view(),
        name="teacher-feedback-submit",
    ),
    path(
        "writing-versions/<int:writing_version_id>/feedback/",
        TeacherFeedbackSubmitView.as_view(),
        name="teacher-feedback-submit-slash",
    ),
    path(
        "teacher-feedback/<int:feedback_id>/download",
        TeacherFeedbackDownloadView.as_view(),
        name="teacher-feedback-download",
    ),
]
