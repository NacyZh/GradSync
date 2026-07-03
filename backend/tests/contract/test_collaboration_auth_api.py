import pytest

from apps.accounts.models import EmailVerificationCode, RoleActivationRequest
from tests.factories.accounts import UserFactory


@pytest.mark.django_db
def test_register_endpoint_accepts_student_registration(api_client):
    response = api_client.post(
        "/api/accounts/register/",
        {
            "email": "new-student@example.com",
            "password": "StrongPass1!",
            "nickname": "New Student",
            "requestedRole": "student",
            "degreeType": "masters",
        },
        format="json",
    )

    assert response.status_code == 202
    assert response.json()["status"] == "pending_email_verification"


@pytest.mark.django_db
def test_verify_email_endpoint_activates_student(api_client):
    api_client.post(
        "/api/accounts/register/",
        {
            "email": "verify-student@example.com",
            "password": "StrongPass1!",
            "nickname": "Verify Student",
            "requestedRole": "student",
            "degreeType": "doctoral",
        },
        format="json",
    )
    code = EmailVerificationCode.objects.get(email="verify-student@example.com").plain_code

    response = api_client.post(
        "/api/accounts/verify-email/",
        {"email": "verify-student@example.com", "code": code},
        format="json",
    )

    assert response.status_code == 200
    assert response.json()["status"] == "active"


@pytest.mark.django_db
def test_role_activation_admin_contract(api_client):
    admin = UserFactory(global_role="admin", status="active")
    api_client.force_authenticate(admin)
    teacher = UserFactory(
        email="teacher-pending@example.com",
        global_role="advisor",
        status="invited",
        requested_role="teacher",
        active_role="pending",
    )
    activation = RoleActivationRequest.objects.create(user=teacher, requested_role="teacher")

    list_response = api_client.get("/api/accounts/admin/role-activations/")
    patch_response = api_client.patch(
        f"/api/accounts/admin/role-activations/{activation.id}/",
        {"action": "approve"},
        format="json",
    )

    assert list_response.status_code == 200
    assert patch_response.status_code == 200
    assert patch_response.json()["status"] == "approved"


@pytest.mark.django_db
def test_me_patch_and_students_contract(api_client):
    admin = UserFactory(global_role="admin", status="active")
    student = UserFactory(
        email="student-option@example.com",
        name="Student Option",
        global_role="student",
        status="active",
        nickname="Alex",
        requested_role="student",
        active_role="student",
    )
    api_client.force_authenticate(admin)

    me_response = api_client.patch("/api/accounts/me/", {"nickname": "Admin Nick"}, format="json")
    students_response = api_client.get("/api/accounts/students/?q=Alex")

    assert me_response.status_code == 200
    assert me_response.json()["nickname"] == "Admin Nick"
    assert students_response.status_code == 200
    assert students_response.json()[0]["id"] == student.id
