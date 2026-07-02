import pytest

from tests.factories.accounts import UserFactory
from tests.helpers import authenticate


@pytest.mark.django_db
def test_account_locale_get_update_and_validation(api_client):
    user = UserFactory(locale="en")
    client = authenticate(api_client, user)

    response = client.get("/api/accounts/locale/")
    assert response.status_code == 200
    assert response.data["locale"] == "en"

    update_response = client.put("/api/accounts/locale/", {"locale": "zh"}, format="json")
    assert update_response.status_code == 200
    assert update_response.data["locale"] == "zh"
    user.refresh_from_db()
    assert user.locale == "zh"

    invalid_response = client.put("/api/accounts/locale/", {"locale": "fr"}, format="json")
    assert invalid_response.status_code == 400
