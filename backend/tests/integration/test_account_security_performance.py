import pytest
from django.contrib.auth import get_user_model
from django.db import connection
from django.test.utils import CaptureQueriesContext

from tests.factories.accounts import UserFactory

User = get_user_model()


@pytest.mark.django_db
def test_session_inventory_query_count_is_bounded(api_client):
    user = UserFactory()
    User.objects.bulk_create(
        [
            User(
                email=f"scale-user-{index}@example.com",
            )
            for index in range(10_000)
        ],
        batch_size=1_000,
    )
    api_client.force_authenticate(user)
    with CaptureQueriesContext(connection) as queries:
        response = api_client.get("/api/accounts/me/sessions/")
    assert response.status_code == 200
    assert len(queries) <= 8
