import pytest

from tests.factories.accounts import UserFactory


@pytest.mark.django_db
def test_login_returns_current_user_on_success(api_client):
    user = UserFactory(global_role="advisor", status="active")
    user.set_password("Sup3r-Secret-Pw")
    user.save()

    response = api_client.post(
        "/api/accounts/login/",
        {"email": user.email, "password": "Sup3r-Secret-Pw"},
        format="json",
    )

    assert response.status_code == 200
    body = response.json()
    assert body["email"] == user.email
    assert body["global_role"] == "advisor"


@pytest.mark.django_db
def test_session_endpoint_reflects_logged_in_user(api_client):
    user = UserFactory(status="active")
    user.set_password("Sup3r-Secret-Pw")
    user.save()
    api_client.post(
        "/api/accounts/login/",
        {"email": user.email, "password": "Sup3r-Secret-Pw"},
        format="json",
    )

    response = api_client.get("/api/accounts/me/")

    assert response.status_code == 200
    assert response.json()["email"] == user.email


@pytest.mark.django_db
def test_logout_clears_session(api_client):
    user = UserFactory(status="active")
    user.set_password("Sup3r-Secret-Pw")
    user.save()
    api_client.post(
        "/api/accounts/login/",
        {"email": user.email, "password": "Sup3r-Secret-Pw"},
        format="json",
    )

    logout_response = api_client.post("/api/accounts/logout/")
    assert logout_response.status_code == 204

    me_response = api_client.get("/api/accounts/me/")
    assert me_response.status_code == 403


@pytest.mark.django_db
def test_session_endpoint_requires_authentication(api_client):
    response = api_client.get("/api/accounts/me/")

    assert response.status_code == 403
