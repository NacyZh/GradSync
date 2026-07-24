import pytest
from rest_framework.test import APIClient
from rest_framework_simplejwt.tokens import RefreshToken

from apps.accounts.models import AccountSession
from tests.factories.accounts import UserFactory

PASSWORD = "Sup3r-Secret-Pw!"


@pytest.mark.django_db
def test_revoked_sid_denies_existing_bearer_token():
    user = UserFactory()
    user.set_password(PASSWORD)
    user.save()
    login = APIClient().post(
        "/api/accounts/login/",
        {"email": user.email, "password": PASSWORD},
        format="json",
    )
    token = login.json()["accessToken"]
    AccountSession.objects.update(status=AccountSession.Status.REVOKED)

    response = APIClient().get(
        "/api/accounts/me/",
        HTTP_AUTHORIZATION=f"Bearer {token}",
    )
    assert response.status_code == 401


@pytest.mark.django_db
def test_legacy_refresh_without_sid_cannot_rotate(api_client, settings):
    user = UserFactory()
    raw_refresh = str(RefreshToken.for_user(user))
    api_client.cookies[settings.JWT_REFRESH_COOKIE_NAME] = raw_refresh
    response = api_client.post("/api/accounts/token/refresh/")
    assert response.status_code == 401
