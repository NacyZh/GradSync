import pytest
from rest_framework.test import APIClient

from tests.factories.accounts import UserFactory

PASSWORD = "Sup3r-Secret-Pw"


def login(client, user):
    return client.post(
        "/api/accounts/login/",
        {"email": user.email, "password": PASSWORD},
        format="json",
    )


@pytest.fixture
def active_user(db):
    user = UserFactory(status="active")
    user.set_password(PASSWORD)
    user.save()
    return user


def test_login_issues_memory_access_token_and_http_only_refresh_cookie(active_user, settings):
    response = login(APIClient(), active_user)

    assert response.status_code == 200
    assert response.json()["accessToken"]
    assert response.json()["accessTokenExpiresAt"].endswith("Z")
    assert response["Cache-Control"] == "no-store"
    refresh_cookie = response.cookies[settings.JWT_REFRESH_COOKIE_NAME]
    assert refresh_cookie["httponly"] is True
    assert refresh_cookie["samesite"] == "Strict"
    assert refresh_cookie["path"] == "/api/accounts/"


def test_bearer_access_token_authenticates_without_session(active_user):
    login_response = login(APIClient(), active_user)
    token = login_response.json()["accessToken"]
    bearer_client = APIClient()

    response = bearer_client.get(
        "/api/accounts/me/",
        HTTP_AUTHORIZATION=f"Bearer {token}",
    )

    assert response.status_code == 200
    assert response.json()["email"] == active_user.email


def test_refresh_requires_csrf_and_rotates_refresh_token(active_user, settings):
    client = APIClient(enforce_csrf_checks=True)
    login_response = login(client, active_user)
    original_refresh = login_response.cookies[settings.JWT_REFRESH_COOKIE_NAME].value
    csrf = login_response.cookies["csrftoken"].value

    rejected = client.post("/api/accounts/token/refresh/")
    assert rejected.status_code == 403

    refreshed = client.post(
        "/api/accounts/token/refresh/",
        HTTP_X_CSRFTOKEN=csrf,
    )
    assert refreshed.status_code == 200
    assert refreshed.json()["accessToken"]
    assert refreshed.cookies[settings.JWT_REFRESH_COOKIE_NAME].value != original_refresh

    client.cookies[settings.JWT_REFRESH_COOKIE_NAME] = original_refresh
    client.cookies["csrftoken"] = csrf
    reused = client.post(
        "/api/accounts/token/refresh/",
        HTTP_X_CSRFTOKEN=csrf,
    )
    assert reused.status_code == 401


def test_suspended_account_cannot_continue_with_existing_bearer_token(active_user):
    token = login(APIClient(), active_user).json()["accessToken"]
    active_user.status = "suspended"
    active_user.save(update_fields=["status"])

    response = APIClient().get(
        "/api/accounts/me/",
        HTTP_AUTHORIZATION=f"Bearer {token}",
    )

    assert response.status_code == 401


def test_password_change_invalidates_previously_issued_access_token(active_user):
    token = login(APIClient(), active_user).json()["accessToken"]
    active_user.set_password("An0ther-Secure-Pw!")
    active_user.save(update_fields=["password"])

    response = APIClient().get(
        "/api/accounts/me/",
        HTTP_AUTHORIZATION=f"Bearer {token}",
    )

    assert response.status_code == 401


def test_token_revoke_blacklists_refresh_cookie(active_user, settings):
    client = APIClient(enforce_csrf_checks=True)
    login_response = login(client, active_user)
    raw_refresh = login_response.cookies[settings.JWT_REFRESH_COOKIE_NAME].value
    csrf = login_response.cookies["csrftoken"].value

    revoked = client.post("/api/accounts/token/revoke/", HTTP_X_CSRFTOKEN=csrf)
    assert revoked.status_code == 204

    client.cookies[settings.JWT_REFRESH_COOKIE_NAME] = raw_refresh
    client.cookies["csrftoken"] = csrf
    retried = client.post("/api/accounts/token/refresh/", HTTP_X_CSRFTOKEN=csrf)
    assert retried.status_code == 401
