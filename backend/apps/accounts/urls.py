from django.urls import path

from .views import (
    AccountDetailView,
    AccountListView,
    CurrentUserView,
    EmailVerificationView,
    LocalePreferenceView,
    LoginView,
    LogoutView,
    PasswordChangeView,
    RegistrationView,
    RoleActivationDetailView,
    RoleActivationListView,
    StudentSearchView,
    VerificationResendView,
)

urlpatterns = [
    path("register/", RegistrationView.as_view(), name="register"),
    path("verify-email/", EmailVerificationView.as_view(), name="verify-email"),
    path("resend-verification/", VerificationResendView.as_view(), name="resend-verification"),
    path("login/", LoginView.as_view(), name="login"),
    path("logout/", LogoutView.as_view(), name="logout"),
    path("me/", CurrentUserView.as_view(), name="current-user"),
    path("me/password/", PasswordChangeView.as_view(), name="password-change"),
    path("students/", StudentSearchView.as_view(), name="student-search"),
    path("locale/", LocalePreferenceView.as_view(), name="locale-preference"),
    path(
        "admin/role-activations/",
        RoleActivationListView.as_view(),
        name="role-activation-list",
    ),
    path(
        "admin/role-activations/<int:pk>/",
        RoleActivationDetailView.as_view(),
        name="role-activation-detail",
    ),
    path("admin/", AccountListView.as_view(), name="account-list"),
    path("admin/<int:pk>/", AccountDetailView.as_view(), name="account-detail"),
]
