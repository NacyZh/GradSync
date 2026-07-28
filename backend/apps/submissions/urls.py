from django.urls import include, path
from rest_framework.routers import DefaultRouter

from .views import (
    InlineCommentViewSet,
    ProjectReportScheduleView,
    ReportAnalyticsExportView,
    ReportAnalyticsView,
    ReportingPeriodListView,
    ReportTemplateDetailView,
    ReportTemplateListView,
    ReportTemplatePublishView,
    StandaloneWritingProjectViewSet,
    StructuredReportListView,
    TeacherFeedbackDownloadView,
    TeacherFeedbackSubmitView,
    WeeklyReportViewSet,
    WritingProjectViewSet,
    WritingVersionDownloadView,
    WritingVersionUploadView,
)

router = DefaultRouter()
standalone_router = DefaultRouter()
standalone_router.register(
    "writing-projects", StandaloneWritingProjectViewSet, basename="standalone-writing"
)
router.register("reports", WeeklyReportViewSet, basename="project-reports")
router.register("comments", InlineCommentViewSet, basename="project-comments")
router.register("writing-projects", WritingProjectViewSet, basename="project-writing")

urlpatterns = [
    path(
        "projects/<int:project_id>/report-templates/",
        ReportTemplateListView.as_view(),
        name="report-template-list",
    ),
    path(
        "projects/<int:project_id>/report-templates/<int:template_version_id>/",
        ReportTemplateDetailView.as_view(),
        name="report-template-detail",
    ),
    path(
        "projects/<int:project_id>/report-templates/<int:template_version_id>/publish/",
        ReportTemplatePublishView.as_view(),
        name="report-template-publish",
    ),
    path(
        "projects/<int:project_id>/reporting-periods/",
        ReportingPeriodListView.as_view(),
        name="reporting-period-list",
    ),
    path(
        "projects/<int:project_id>/structured-reports/",
        StructuredReportListView.as_view(),
        name="structured-report-list",
    ),
    path(
        "projects/<int:project_id>/report-analytics/",
        ReportAnalyticsView.as_view(),
        name="report-analytics",
    ),
    path(
        "projects/<int:project_id>/report-analytics/export/",
        ReportAnalyticsExportView.as_view(),
        name="report-analytics-export",
    ),
    path(
        "projects/<int:project_id>/report-schedule/",
        ProjectReportScheduleView.as_view(),
        name="project-report-schedule",
    ),
    path("", include(standalone_router.urls)),
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
        "writing-versions/<int:writing_version_id>/download",
        WritingVersionDownloadView.as_view(),
        name="writing-version-download",
    ),
    path(
        "writing-versions/<int:writing_version_id>/download/",
        WritingVersionDownloadView.as_view(),
        name="writing-version-download-slash",
    ),
    path(
        "teacher-feedback/<int:feedback_id>/download",
        TeacherFeedbackDownloadView.as_view(),
        name="teacher-feedback-download",
    ),
]
