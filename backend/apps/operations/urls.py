from django.urls import path

from .views import ProjectHealthSnapshotView

urlpatterns = [
    path(
        "admin/project-health/",
        ProjectHealthSnapshotView.as_view(),
        name="admin-project-health",
    ),
]
