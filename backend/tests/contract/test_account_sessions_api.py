import pytest

from apps.accounts.models import AccountSession
from tests.factories.accounts import UserFactory

PASSWORD = "Sup3r-Secret-Pw!"


def login(client, user):
    return client.post(
        "/api/accounts/login/",
        {"email": user.email, "password": PASSWORD},
        format="json",
    )


@pytest.mark.django_db
def test_session_inventory_and_revoke_others(api_client):
    user = UserFactory()
    user.set_password(PASSWORD)
    user.save()
    login(api_client, user)
    current_id = api_client.session["account_session_id"]
    AccountSession.objects.create(
        user=user,
        status=AccountSession.Status.ACTIVE,
        device_label="Other browser",
        expires_at=AccountSession.default_expiry(),
    )

    response = api_client.get("/api/accounts/me/sessions/")
    assert response.status_code == 200
    assert response.json()["results"][0]["id"] == current_id
    assert response.json()["results"][0]["current"] is True
    assert "django_session_key_hash" not in response.json()["results"][0]

    revoked = api_client.post("/api/accounts/me/sessions/revoke-others/")
    assert revoked.status_code == 200
    assert revoked.json()["revokedCount"] == 1


@pytest.mark.django_db
def test_current_session_cannot_be_revoked_from_inventory(api_client):
    user = UserFactory()
    user.set_password(PASSWORD)
    user.save()
    login(api_client, user)
    current_id = api_client.session["account_session_id"]

    response = api_client.delete(f"/api/accounts/me/sessions/{current_id}/")
    assert response.status_code == 400
