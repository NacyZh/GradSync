import pytest

from apps.accounts.models import EmailVerificationCode, RoleActivationRequest, StudentProfile
from tests.factories.accounts import UserFactory


def register(api_client, **overrides):
    payload = {
        "email": "person@example.com",
        "password": "StrongPass1!",
        "nickname": "Person",
        "requestedRole": "student",
        "degreeType": "masters",
    }
    payload.update(overrides)
    return api_client.post("/api/accounts/register/", payload, format="json")


@pytest.mark.django_db
def test_weak_password_is_rejected(api_client):
    response = register(api_client, password="weak")

    assert response.status_code == 400
    assert "Password" in response.json()["message"]


@pytest.mark.django_db
def test_student_degree_type_is_required(api_client):
    response = register(api_client, degreeType="")

    assert response.status_code == 400
    assert "degree" in response.json()["message"].lower()


@pytest.mark.django_db
def test_student_becomes_active_after_email_verification(api_client):
    register(api_client, email="student-active@example.com", degreeType="doctoral")
    code = EmailVerificationCode.objects.get(email="student-active@example.com").plain_code

    response = api_client.post(
        "/api/accounts/verify-email/",
        {"email": "student-active@example.com", "code": code},
        format="json",
    )

    assert response.status_code == 200
    assert response.json()["status"] == "active"
    assert StudentProfile.objects.get(user__email="student-active@example.com").degree_type == "doctoral"


@pytest.mark.django_db
def test_teacher_remains_pending_until_admin_approval(api_client):
    register(
        api_client,
        email="teacher@example.com",
        requestedRole="teacher",
        degreeType=None,
    )
    code = EmailVerificationCode.objects.get(email="teacher@example.com").plain_code

    verify_response = api_client.post(
        "/api/accounts/verify-email/",
        {"email": "teacher@example.com", "code": code},
        format="json",
    )

    assert verify_response.status_code == 200
    assert verify_response.json()["status"] == "pending_role_activation"
    assert RoleActivationRequest.objects.filter(user__email="teacher@example.com", status="pending").exists()


@pytest.mark.django_db
def test_admin_approval_activates_teacher(api_client):
    admin = UserFactory(global_role="admin", status="active")
    register(api_client, email="teacher-approve@example.com", requestedRole="teacher", degreeType=None)
    code = EmailVerificationCode.objects.get(email="teacher-approve@example.com").plain_code
    api_client.post(
        "/api/accounts/verify-email/",
        {"email": "teacher-approve@example.com", "code": code},
        format="json",
    )
    activation = RoleActivationRequest.objects.get(user__email="teacher-approve@example.com")
    api_client.force_authenticate(admin)

    response = api_client.patch(
        f"/api/accounts/admin/role-activations/{activation.id}/",
        {"action": "approve"},
        format="json",
    )

    assert response.status_code == 200
    assert response.json()["status"] == "approved"
    assert response.json()["user"]["status"] == "active"
