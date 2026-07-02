from django.urls import path

from .views import (
    AccountDetailView,
    AccountListCreateView,
    CurrentUserView,
    LocalePreferenceView,
    LoginView,
    LogoutView,
)

urlpatterns = [
    path("login/", LoginView.as_view(), name="login"),
    path("logout/", LogoutView.as_view(), name="logout"),
    path("me/", CurrentUserView.as_view(), name="current-user"),
    path("locale/", LocalePreferenceView.as_view(), name="locale-preference"),
    path("admin/", AccountListCreateView.as_view(), name="account-list-create"),
    path("admin/<int:pk>/", AccountDetailView.as_view(), name="account-detail"),
]
