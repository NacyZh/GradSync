from django.urls import include, path
from rest_framework.routers import DefaultRouter

from .views import (
    NotificationAcknowledgeView,
    NotificationOperationsSummaryView,
    NotificationPreferenceView,
    NotificationReadView,
    NotificationStatusListView,
    ProjectNotificationPolicyView,
    ProjectNotificationViewSet,
)

router = DefaultRouter()
router.register("notifications", ProjectNotificationViewSet, basename="project-notifications")

urlpatterns = [
    path("notifications/read", NotificationReadView.as_view(), name="notification-read"),
    path(
        "notifications/<int:notification_id>/acknowledge",
        NotificationAcknowledgeView.as_view(),
        name="notification-acknowledge",
    ),
    path("notifications", NotificationStatusListView.as_view(), name="notification-status-list"),
    path(
        "notification-preferences",
        NotificationPreferenceView.as_view(),
        name="notification-preferences",
    ),
    path(
        "projects/<int:project_id>/notification-policy",
        ProjectNotificationPolicyView.as_view(),
        name="project-notification-policy",
    ),
    path(
        "admin/notifications/summary",
        NotificationOperationsSummaryView.as_view(),
        name="notification-operations-summary",
    ),
    path("projects/<int:project_id>/", include(router.urls)),
]
