import pytest
from django.contrib.auth import get_user_model

from tests.factories.accounts import UserFactory

User = get_user_model()
PASSWORD = "Sup3r-Secret-Pw"


def _force_login(api_client, user):
    """Helper: log the given user in via the session API."""
    user.set_password(PASSWORD)
    user.save()
    api_client.post(
        "/api/accounts/login/", {"email": user.email, "password": PASSWORD}, format="json"
    )
    # Re-fetch to get the CSRF token set on the next request.
    api_client.get("/api/accounts/me/")


@pytest.mark.django_db
class TestAdminAccountManagement:
    def test_admin_can_create_advisor_account(self, api_client):
        admin = UserFactory(global_role="admin", status="active")
        _force_login(api_client, admin)

        response = api_client.post(
            "/api/accounts/admin/",
            {"email": "new-advisor@example.com", "name": "New Advisor", "global_role": "advisor"},
            format="json",
        )

        assert response.status_code == 201
        data = response.json()
        assert data["email"] == "new-advisor@example.com"
        assert data["global_role"] == "advisor"
        assert data["status"] == "invited"

    def test_admin_can_create_student_account(self, api_client):
        admin = UserFactory(global_role="admin", status="active")
        _force_login(api_client, admin)

        response = api_client.post(
            "/api/accounts/admin/",
            {"email": "new-student@example.com", "name": "New Student", "global_role": "student"},
            format="json",
        )

        assert response.status_code == 201
        assert response.json()["status"] == "invited"
        # Created account has no usable password.
        user = User.objects.get(email="new-student@example.com")
        assert not user.has_usable_password()

    def test_duplicate_email_rejected(self, api_client):
        admin = UserFactory(global_role="admin", status="active")
        _force_login(api_client, admin)
        UserFactory(email="exists@example.com")

        response = api_client.post(
            "/api/accounts/admin/",
            {"email": "exists@example.com", "name": "Dup", "global_role": "student"},
            format="json",
        )

        assert response.status_code == 400

    def test_non_admin_cannot_create_account(self, api_client):
        advisor = UserFactory(global_role="advisor", status="active")
        _force_login(api_client, advisor)

        response = api_client.post(
            "/api/accounts/admin/",
            {"email": "foo@example.com", "name": "Foo", "global_role": "student"},
            format="json",
        )

        assert response.status_code == 403

    def test_non_admin_cannot_list_accounts(self, api_client):
        student = UserFactory(global_role="student", status="active")
        _force_login(api_client, student)

        response = api_client.get("/api/accounts/admin/")

        assert response.status_code == 403

    def test_admin_can_list_accounts_paginated(self, api_client):
        admin = UserFactory(global_role="admin", status="active")
        _force_login(api_client, admin)
        UserFactory.create_batch(3, status="active")

        response = api_client.get("/api/accounts/admin/")

        assert response.status_code == 200
        data = response.json()
        assert "results" in data
        assert len(data["results"]) >= 4  # admin + 3 created

    def test_admin_can_suspend_and_reactivate_account(self, api_client):
        admin = UserFactory(global_role="admin", status="active")
        _force_login(api_client, admin)
        student = UserFactory(global_role="student", status="active")

        # Suspend.
        response = api_client.post(
            f"/api/accounts/admin/{student.pk}/",
            {"action": "suspend"},
            format="json",
        )
        assert response.status_code == 200
        assert response.json()["status"] == "suspended"

        # Suspended user cannot sign in.
        student.refresh_from_db()
        assert not student.is_active

        # Reactivate.
        response = api_client.post(
            f"/api/accounts/admin/{student.pk}/",
            {"action": "reactivate"},
            format="json",
        )
        assert response.status_code == 200
        assert response.json()["status"] == "active"

    def test_admin_can_edit_account_name_and_role(self, api_client):
        admin = UserFactory(global_role="admin", status="active")
        _force_login(api_client, admin)
        target = UserFactory(global_role="student", status="active", name="Old Name")

        response = api_client.patch(
            f"/api/accounts/admin/{target.pk}/",
            {"name": "Updated Name", "global_role": "advisor"},
            format="json",
        )

        assert response.status_code == 200
        data = response.json()
        assert data["name"] == "Updated Name"
        assert data["global_role"] == "advisor"


@pytest.mark.django_db
class TestLastAdminProtection:
    def test_cannot_suspend_last_admin(self, api_client):
        admin = UserFactory(global_role="admin", status="active")
        _force_login(api_client, admin)

        response = api_client.post(
            f"/api/accounts/admin/{admin.pk}/",
            {"action": "suspend"},
            format="json",
        )

        assert response.status_code == 400
        assert "last active administrator" in response.json()["message"]

    def test_cannot_demote_last_admin(self, api_client):
        admin = UserFactory(global_role="admin", status="active")
        _force_login(api_client, admin)

        response = api_client.patch(
            f"/api/accounts/admin/{admin.pk}/",
            {"global_role": "student"},
            format="json",
        )

        assert response.status_code == 400
        assert "last active administrator" in response.json()["message"]
