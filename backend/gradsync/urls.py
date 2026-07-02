from django.contrib import admin
from django.urls import include, path
from drf_spectacular.views import SpectacularAPIView, SpectacularSwaggerView

from apps.accounts.views import LocalePreferenceView
from apps.common.views import healthz, metrics, readyz

urlpatterns = [
    path("healthz/", healthz, name="healthz"),
    path("readyz/", readyz, name="readyz"),
    path("metrics/", metrics, name="metrics"),
    path("admin/", admin.site.urls),
    path("api/accounts/", include("apps.accounts.urls")),
    path("api/account/locale/", LocalePreferenceView.as_view(), name="contract-locale-preference"),
    path("api/", include("apps.projects.urls")),
    path("api/", include("apps.tasks.urls")),
    path("api/", include("apps.submissions.urls")),
    path("api/", include("apps.resources.urls")),
    path("api/", include("apps.library.urls")),
    path("api/", include("apps.repositories.urls")),
    path("api/", include("apps.notifications.urls")),
    path("api/schema/", SpectacularAPIView.as_view(), name="schema"),
    path("api/docs/", SpectacularSwaggerView.as_view(url_name="schema"), name="swagger-ui"),
]
