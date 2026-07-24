from django.urls import path
from rest_framework.routers import DefaultRouter

from .views import EligibleTeacherSearchView, LegacyBoundaryLinkView, ProjectViewSet

router = DefaultRouter()
router.register("projects", ProjectViewSet, basename="projects")

urlpatterns = [
    path("boundary/legacy-link/", LegacyBoundaryLinkView.as_view(), name="legacy-boundary-link"),
    path(
        "projects/collaborators/eligible/",
        EligibleTeacherSearchView.as_view(),
        name="eligible-project-teachers",
    ),
    path(
        "accounts/teachers/",
        EligibleTeacherSearchView.as_view(),
        name="eligible-account-teachers",
    ),
    *router.urls,
]
