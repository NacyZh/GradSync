import pytest

from apps.accounts.models import (
    EmailVerificationCode,
    RoleActivationRequest,
    StudentProfile,
    TeacherProfile,
)
from apps.audit.models import AuditEvent
from tests.factories.accounts import UserFactory


def register(api_client, **overrides):
    payload = {
        "email": "person@example.com",
        "password": "StrongPass1!",
        "name": "Person Example",
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
def test_public_registration_rejects_administrator_role(api_client):
    response = register(api_client, requestedRole="administrator", degreeType=None)

    assert response.status_code == 400


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
    assert (
        StudentProfile.objects.get(user__email="student-active@example.com").degree_type
        == "doctoral"
    )


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
    assert RoleActivationRequest.objects.filter(
        user__email="teacher@example.com", status="pending"
    ).exists()


@pytest.mark.django_db
def test_admin_approval_activates_teacher(api_client):
    admin = UserFactory(global_role="admin", status="active")
    register(
        api_client, email="teacher-approve@example.com", requestedRole="teacher", degreeType=None
    )
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


@pytest.mark.django_db
def test_teacher_rejection_requires_reason_and_allows_secure_resubmission(api_client):
    admin = UserFactory(global_role="admin", status="active")
    register(
        api_client,
        email="teacher-resubmit@example.com",
        requestedRole="teacher",
        degreeType=None,
    )
    code = EmailVerificationCode.objects.get(
        email="teacher-resubmit@example.com"
    ).plain_code
    api_client.post(
        "/api/accounts/verify-email/",
        {"email": "teacher-resubmit@example.com", "code": code},
        format="json",
    )
    activation = RoleActivationRequest.objects.get(
        user__email="teacher-resubmit@example.com"
    )
    api_client.force_authenticate(admin)

    missing_reason = api_client.patch(
        f"/api/accounts/admin/role-activations/{activation.id}/",
        {"action": "reject"},
        format="json",
    )
    rejected = api_client.patch(
        f"/api/accounts/admin/role-activations/{activation.id}/",
        {"action": "reject", "reason": "Use your institutional display name."},
        format="json",
    )
    repeated = api_client.patch(
        f"/api/accounts/admin/role-activations/{activation.id}/",
        {"action": "approve"},
        format="json",
    )
    api_client.force_authenticate(user=None)
    resubmitted = register(
        api_client,
        email="teacher-resubmit@example.com",
        password="StrongPass1!",
        name="Corrected Teacher",
        nickname="Corrected",
        requestedRole="teacher",
        degreeType=None,
    )

    assert missing_reason.status_code == 400
    assert rejected.status_code == 200
    assert rejected.json()["reviewReason"] == "Use your institutional display name."
    assert rejected.json()["reviewer"]["id"] == admin.id
    assert repeated.status_code == 409
    assert resubmitted.status_code == 202
    assert resubmitted.json()["status"] == "pending_role_activation"
    requests = RoleActivationRequest.objects.filter(
        user__email="teacher-resubmit@example.com"
    ).order_by("created_at")
    assert [request.status for request in requests] == ["rejected", "pending"]
    assert requests.last().user.name == "Corrected Teacher"


@pytest.mark.django_db
def test_rejected_teacher_cannot_resubmit_with_the_wrong_password(api_client):
    admin = UserFactory(global_role="admin", status="active")
    register(
        api_client,
        email="teacher-secure-resubmit@example.com",
        requestedRole="teacher",
        degreeType=None,
    )
    code = EmailVerificationCode.objects.get(
        email="teacher-secure-resubmit@example.com"
    ).plain_code
    api_client.post(
        "/api/accounts/verify-email/",
        {"email": "teacher-secure-resubmit@example.com", "code": code},
        format="json",
    )
    activation = RoleActivationRequest.objects.get(
        user__email="teacher-secure-resubmit@example.com"
    )
    api_client.force_authenticate(admin)
    api_client.patch(
        f"/api/accounts/admin/role-activations/{activation.id}/",
        {"action": "reject", "reason": "Correct the submitted profile."},
        format="json",
    )
    api_client.force_authenticate(user=None)

    response = register(
        api_client,
        email="teacher-secure-resubmit@example.com",
        password="WrongPass1!",
        requestedRole="teacher",
        degreeType=None,
    )

    assert response.status_code == 400
    assert RoleActivationRequest.objects.filter(
        user__email="teacher-secure-resubmit@example.com"
    ).count() == 1


@pytest.mark.django_db
def test_revoking_teacher_access_removes_profile_and_records_reason(api_client):
    admin = UserFactory(global_role="admin", status="active")
    register(
        api_client,
        email="teacher-revoke@example.com",
        requestedRole="teacher",
        degreeType=None,
    )
    code = EmailVerificationCode.objects.get(
        email="teacher-revoke@example.com"
    ).plain_code
    api_client.post(
        "/api/accounts/verify-email/",
        {"email": "teacher-revoke@example.com", "code": code},
        format="json",
    )
    activation = RoleActivationRequest.objects.get(
        user__email="teacher-revoke@example.com"
    )
    api_client.force_authenticate(admin)
    api_client.patch(
        f"/api/accounts/admin/role-activations/{activation.id}/",
        {"action": "approve"},
        format="json",
    )

    response = api_client.patch(
        f"/api/accounts/admin/role-activations/{activation.id}/",
        {"action": "revoke", "reason": "Employment ended."},
        format="json",
    )

    assert response.status_code == 200
    activation.refresh_from_db()
    activation.user.refresh_from_db()
    assert activation.status == RoleActivationRequest.Status.REVOKED
    assert activation.review_reason == "Employment ended."
    assert activation.user.status == "pending_role_activation"
    assert activation.user.active_role == "pending"
    assert not TeacherProfile.objects.filter(user=activation.user).exists()
    audit = AuditEvent.objects.get(
        event_type="role_activation.revoke", target_id=str(activation.id)
    )
    assert audit.target_snapshot["reason"] == "Employment ended."

    bypass_response = api_client.post(
        f"/api/accounts/admin/{activation.user_id}/",
        {"action": "reactivate"},
        format="json",
    )
    assert bypass_response.status_code == 400
    activation.user.refresh_from_db()
    assert activation.user.status == "pending_role_activation"


@pytest.mark.django_db
def test_user_updates_personal_profile(api_client):
    student = UserFactory(
        global_role="student",
        status="active",
        nickname="Old Nick",
        requested_role="student",
        active_role="student",
    )
    StudentProfile.objects.create(user=student, degree_type="masters")
    api_client.force_authenticate(student)

    response = api_client.patch(
        "/api/accounts/me/",
        {"name": "Student Name", "nickname": "New Nick", "degreeType": "doctoral"},
        format="json",
    )

    assert response.status_code == 200
    assert response.json()["name"] == "Student Name"
    assert response.json()["nickname"] == "New Nick"
    assert response.json()["degreeType"] == "doctoral"


@pytest.mark.django_db
def test_user_changes_password_and_keeps_session(api_client):
    student = UserFactory(global_role="student", status="active")
    student.set_password("CurrentPass1!")
    student.save(update_fields=["password"])
    api_client.post(
        "/api/accounts/login/",
        {"email": student.email, "password": "CurrentPass1!"},
        format="json",
    )

    response = api_client.post(
        "/api/accounts/me/password/",
        {"currentPassword": "CurrentPass1!", "newPassword": "ChangedPass2!"},
        format="json",
    )

    assert response.status_code == 204
    assert api_client.get("/api/accounts/me/").status_code == 200
    student.refresh_from_db()
    assert student.check_password("ChangedPass2!")


@pytest.mark.django_db
def test_pending_user_can_request_a_new_verification_code(api_client):
    register(api_client, email="resend@example.com")
    original = EmailVerificationCode.objects.get(email="resend@example.com")

    response = api_client.post(
        "/api/accounts/resend-verification/",
        {"email": "resend@example.com"},
        format="json",
    )

    assert response.status_code == 202
    original.refresh_from_db()
    assert original.status == EmailVerificationCode.Status.REVOKED
    assert (
        EmailVerificationCode.objects.filter(
            email="resend@example.com", status=EmailVerificationCode.Status.PENDING
        ).count()
        == 1
    )
