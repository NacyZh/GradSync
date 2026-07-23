import pytest
from django.test import override_settings

from tests.factories.accounts import UserFactory
from tests.helpers import authenticate


@pytest.mark.django_db
@override_settings(
    GRADSYNC_UPLOAD_MAX_BYTES=7 * 1024 * 1024,
    COLLABORATION_UPLOAD_LIMITS={
        category: 7 * 1024 * 1024
        for category in ("paper", "code", "document", "writing", "feedback")
    },
)
def test_upload_policies_share_the_environment_limit(api_client):
    user = UserFactory(global_role="student", status="active")
    client = authenticate(api_client, user)

    for category in ("paper", "code", "document", "writing", "feedback"):
        response = client.get(f"/api/upload-policies/{category}/")

        assert response.status_code == 200
        assert response.data["category"] == category
        assert response.data["maxSizeBytes"] == 7 * 1024 * 1024
        assert response.data["displayLabel"] == "7 MB"
        assert response.data["allowedExtensions"]


@pytest.mark.django_db
def test_upload_policy_rejects_unknown_category_and_requires_authentication(api_client):
    assert api_client.get("/api/upload-policies/document/").status_code == 401

    user = UserFactory(global_role="student", status="active")
    response = authenticate(api_client, user).get("/api/upload-policies/video/")

    assert response.status_code == 404
