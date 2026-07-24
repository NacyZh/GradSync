from django.urls import path

from .views import (
    AuditEventDetailView,
    AuditEventListView,
    AuditExportCreateView,
    AuditExportDetailView,
    AuditExportDownloadView,
)

urlpatterns = [
    path("audit-events", AuditEventListView.as_view(), name="audit-event-list"),
    path("audit-events/<int:event_id>", AuditEventDetailView.as_view(), name="audit-event-detail"),
    path("audit-exports", AuditExportCreateView.as_view(), name="audit-export-create"),
    path(
        "audit-exports/<uuid:export_id>",
        AuditExportDetailView.as_view(),
        name="audit-export-detail",
    ),
    path(
        "audit-exports/<uuid:export_id>/download",
        AuditExportDownloadView.as_view(),
        name="audit-export-download",
    ),
]
