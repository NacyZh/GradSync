import re

import pytest
from django.core import mail
from django.utils import timezone

from apps.accounts.models import AccountRecoveryRequest, EmailChangeRequest
from tests.factories.accounts import UserFactory

PASSWORD = "Sup3r-Secret-Pw!"
NEW_PASSWORD = "An0ther-Secure-Pw!"


@pytest.mark.django_db
@pytest.mark.parametrize("kind", ["eligible", "unknown", "suspended", "archived"])
def test_password_recovery_request_is_non_enumerating(api_client, kind, settings):
    settings.EMAIL_BACKEND = "django.core.mail.backends.locmem.EmailBackend"
    settings.PUBLIC_BASE_URL = "https://public.gradsync.example"
    email = f"{kind}@example.com"
    if kind != "unknown":
        user = UserFactory(
            email=email,
            status="active" if kind == "eligible" else kind,
            email_verified_at=timezone.now(),
        )
        user.set_password(PASSWORD)
        user.save()

    response = api_client.post(
        "/api/accounts/password-recovery/",
        {"email": email, "returnTo": "/reset-password"},
        format="json",
    )

    assert response.status_code == 202
    assert response.json() == {
        "message": "If the account is eligible, recovery instructions will be sent."
    }
    assert AccountRecoveryRequest.objects.count() == (1 if kind == "eligible" else 0)
    if kind == "eligible":
        assert (
            "https://public.gradsync.example/reset-password?"
            in mail.outbox[-1].body
        )


@pytest.mark.django_db
def test_password_recovery_confirmation_changes_password_and_is_single_use(api_client, settings):
    settings.EMAIL_BACKEND = "django.core.mail.backends.locmem.EmailBackend"
    user = UserFactory(email_verified_at=timezone.now())
    user.set_password(PASSWORD)
    user.save()
    api_client.post(
        "/api/accounts/password-recovery/",
        {"email": user.email},
        format="json",
    )
    request = AccountRecoveryRequest.objects.get(user=user)
    token = re.search(r"token=([^&\s]+)", mail.outbox[-1].body).group(1)

    payload = {"requestId": str(request.id), "token": token, "newPassword": NEW_PASSWORD}
    assert (
        api_client.post(
            "/api/accounts/password-recovery/confirm/", payload, format="json"
        ).status_code
        == 204
    )
    assert (
        api_client.post(
            "/api/accounts/password-recovery/confirm/", payload, format="json"
        ).status_code
        == 409
    )
    user.refresh_from_db()
    assert user.check_password(NEW_PASSWORD)


@pytest.mark.django_db
def test_password_recovery_confirmation_signs_out_current_browser(api_client, settings):
    settings.EMAIL_BACKEND = "django.core.mail.backends.locmem.EmailBackend"
    signed_in_user = UserFactory(email_verified_at=timezone.now())
    signed_in_user.set_password(PASSWORD)
    signed_in_user.save()
    recovered_user = UserFactory(email_verified_at=timezone.now())
    recovered_user.set_password(PASSWORD)
    recovered_user.save()

    login_response = api_client.post(
        "/api/accounts/login/",
        {"email": signed_in_user.email, "password": PASSWORD},
        format="json",
    )
    assert login_response.status_code == 200
    api_client.post(
        "/api/accounts/password-recovery/",
        {"email": recovered_user.email},
        format="json",
    )
    recovery = AccountRecoveryRequest.objects.get(user=recovered_user)
    token = re.search(r"token=([^&\s]+)", mail.outbox[-1].body).group(1)

    response = api_client.post(
        "/api/accounts/password-recovery/confirm/",
        {
            "requestId": str(recovery.id),
            "token": token,
            "newPassword": NEW_PASSWORD,
        },
        format="json",
    )

    assert response.status_code == 204
    assert response["Cache-Control"] == "no-store"
    assert response.cookies[settings.JWT_REFRESH_COOKIE_NAME]["max-age"] == 0
    assert api_client.get("/api/accounts/me/").status_code == 401


@pytest.mark.django_db
def test_email_change_keeps_old_email_until_verified(api_client, settings):
    settings.EMAIL_BACKEND = "django.core.mail.backends.locmem.EmailBackend"
    user = UserFactory(email_verified_at=timezone.now())
    user.set_password(PASSWORD)
    user.save()
    api_client.force_authenticate(user)

    response = api_client.post(
        "/api/accounts/me/email-change/",
        {"newEmail": "replacement@example.com", "currentPassword": PASSWORD},
        format="json",
    )

    assert response.status_code == 202
    user.refresh_from_db()
    assert user.email != "replacement@example.com"
    change = EmailChangeRequest.objects.get(user=user)
    code = re.search(r"code is ([0-9]+)", mail.outbox[-1].body).group(1)
    verified = api_client.post(
        "/api/accounts/me/email-change/verify/",
        {"requestId": str(change.id), "code": code},
        format="json",
    )
    assert verified.status_code == 200
    user.refresh_from_db()
    assert user.email == "replacement@example.com"
