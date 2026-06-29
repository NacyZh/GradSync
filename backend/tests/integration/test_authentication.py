import pytest

from tests.factories.accounts import UserFactory

PASSWORD = "Sup3r-Secret-Pw"


def _login(api_client, email, password):
    return api_client.post(
        "/api/accounts/login/",
        {"email": email, "password": password},
        format="json",
    )


@pytest.mark.django_db
def test_active_user_can_sign_in(api_client):
    user = UserFactory(status="active")
    user.set_password(PASSWORD)
    user.save()

    response = _login(api_client, user.email, PASSWORD)

    assert response.status_code == 200


@pytest.mark.django_db
def test_wrong_password_is_rejected_with_generic_message(api_client):
    user = UserFactory(status="active")
    user.set_password(PASSWORD)
    user.save()

    response = _login(api_client, user.email, "wrong-password")

    assert response.status_code == 400
    assert response.json()["message"] == "Invalid email or password."


@pytest.mark.django_db
def test_unknown_email_does_not_enumerate(api_client):
    response = _login(api_client, "nobody@example.com", PASSWORD)

    assert response.status_code == 400
    # Identical message to the wrong-password case: no account enumeration.
    assert response.json()["message"] == "Invalid email or password."


@pytest.mark.django_db
@pytest.mark.parametrize("status", ["suspended", "archived", "invited"])
def test_non_active_account_cannot_sign_in(api_client, status):
    user = UserFactory(status=status)
    user.set_password(PASSWORD)
    user.save()

    response = _login(api_client, user.email, PASSWORD)

    assert response.status_code == 400
    assert "not active" in response.json()["message"]
