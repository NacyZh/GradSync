from django.contrib import admin
from django.urls import include, path
from drf_spectacular.views import SpectacularAPIView, SpectacularSwaggerView

from apps.accounts.views import (
    CurrentUserView,
    EmailVerificationView,
    LocalePreferenceView,
    RegistrationView,
    RoleActivationDetailView,
    RoleActivationListView,
    StudentSearchView,
)
from apps.common.views import UploadPolicyView, healthz, metrics, readyz

urlpatterns = [
    path("healthz/", healthz, name="healthz"),
    path("readyz/", readyz, name="readyz"),
    path("metrics/", metrics, name="metrics"),
    path("admin/", admin.site.urls),
    path("api/auth/register", RegistrationView.as_view(), name="contract-register"),
    path("api/auth/verify-email", EmailVerificationView.as_view(), name="contract-verify-email"),
    path(
        "api/admin/role-activations",
        RoleActivationListView.as_view(),
        name="contract-role-activation-list",
    ),
    path(
        "api/admin/role-activations/<int:pk>",
        RoleActivationDetailView.as_view(),
        name="contract-role-activation-detail",
    ),
    path("api/me", CurrentUserView.as_view(), name="contract-current-user"),
    path("api/students", StudentSearchView.as_view(), name="contract-student-search"),
    path("api/accounts/", include("apps.accounts.urls")),
    path("api/account/locale/", LocalePreferenceView.as_view(), name="contract-locale-preference"),
    path(
        "api/upload-policies/<str:category>/",
        UploadPolicyView.as_view(),
        name="upload-policy",
    ),
    path("api/", include("apps.projects.urls")),
    path("api/", include("apps.tasks.urls")),
    path("api/", include("apps.submissions.urls")),
    path("api/", include("apps.resources.urls")),
    path("api/", include("apps.library.urls")),
    path("api/", include("apps.repositories.urls")),
    path("api/", include("apps.notifications.urls")),
    path("api/", include("apps.audit.urls")),
    path("api/", include("apps.schedules.urls")),
    path("api/schema/", SpectacularAPIView.as_view(), name="schema"),
    path("api/docs/", SpectacularSwaggerView.as_view(url_name="schema"), name="swagger-ui"),
]
