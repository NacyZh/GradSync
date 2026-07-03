import pytest

# Representative read endpoints across every feature app. Each must reject
# anonymous access now that DRF defaults to IsAuthenticated globally.
ANONYMOUS_REJECTED_ENDPOINTS = [
    "/api/projects/",
    "/api/resource-items/",
    "/api/projects/1/tasks/",
    "/api/projects/1/drafts/",
    "/api/projects/1/reports/",
    "/api/projects/1/comments/",
    "/api/projects/1/bookings/",
    "/api/projects/1/notifications/",
    "/api/accounts/me/",
]


@pytest.mark.django_db
@pytest.mark.parametrize("path", ANONYMOUS_REJECTED_ENDPOINTS)
def test_endpoint_rejects_anonymous_access(api_client, path):
    response = api_client.get(path)

    assert response.status_code in (401, 403), (
        f"{path} returned {response.status_code}; expected an auth rejection"
    )
