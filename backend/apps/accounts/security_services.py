import hashlib
import hmac
import secrets
from datetime import timedelta
from urllib.parse import urlencode

from django.conf import settings
from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError
from django.core.mail import send_mail
from django.db import IntegrityError, transaction
from django.utils import timezone

from apps.audit.models import AuditEvent
from apps.audit.services import record_event
from apps.notifications.models import Notification
from apps.notifications.services import (
    enqueue_notification,
    mark_notification_attempt_failed,
    mark_notification_status,
)

from .models import AccountRecoveryRequest, EmailChangeRequest
from .services import validate_collaboration_password
from .session_services import revoke_user_sessions

User = get_user_model()
GENERIC_RECOVERY_MESSAGE = "If the account is eligible, recovery instructions will be sent."


def _hash_secret(raw_value: str, purpose: str) -> str:
    return hmac.new(
        settings.SECRET_KEY.encode(),
        f"{purpose}:{raw_value}".encode(),
        hashlib.sha256,
    ).hexdigest()


def _safe_delivery(*, notification: Notification, recipient_email: str, body: str) -> Notification:
    notification.recipient_email = recipient_email
    notification.save(update_fields=["recipient_email"])
    mark_notification_status(notification, Notification.Status.QUEUED)
    try:
        delivered = send_mail(
            notification.subject,
            body,
            settings.DEFAULT_FROM_EMAIL,
            [recipient_email],
            fail_silently=False,
        )
        if delivered != 1:
            raise RuntimeError("SMTP backend did not accept the security email.")
    except Exception as exc:
        return mark_notification_attempt_failed(notification, exc)
    return mark_notification_status(notification, Notification.Status.SENT)


@transaction.atomic
def issue_password_recovery(
    *,
    user,
    requested_ip_hash: str = "",
    requested_user_agent: str = "",
) -> tuple[AccountRecoveryRequest, str]:
    user = User.objects.select_for_update().get(pk=user.pk)
    now = timezone.now()
    AccountRecoveryRequest.objects.filter(
        user=user, status=AccountRecoveryRequest.Status.PENDING
    ).update(
        status=AccountRecoveryRequest.Status.SUPERSEDED,
        superseded_at=now,
        updated_at=now,
    )
    raw_token = secrets.token_urlsafe(32)
    recovery = AccountRecoveryRequest.objects.create(
        user=user,
        token_hash=_hash_secret(raw_token, "password-recovery"),
        requested_email_snapshot=user.email,
        requested_ip_hash=requested_ip_hash[:64],
        requested_user_agent=requested_user_agent[:255],
        expires_at=now + timedelta(seconds=settings.ACCOUNT_RECOVERY_TOKEN_TTL_SECONDS),
    )
    record_event(
        None,
        None,
        "account_security.password_recovery_issued",
        "Password recovery issued",
        recovery,
        category=AuditEvent.Category.ACCOUNT_SECURITY,
        outcome=AuditEvent.Outcome.QUEUED,
        target_snapshot={"status": recovery.status, "userId": user.id},
        allowed_snapshot_keys={"status", "userId"},
    )
    return recovery, raw_token


def deliver_password_recovery(
    *,
    recovery: AccountRecoveryRequest,
    raw_token: str,
    return_to: str = "/reset-password",
) -> Notification:
    query = urlencode({"requestId": str(recovery.id), "token": raw_token})
    path = (
        return_to
        if return_to.startswith("/") and not return_to.startswith("//")
        else "/reset-password"
    )
    url = f"{settings.APPROVED_FRONTEND_ORIGIN}{path}?{query}"
    prefix = str(getattr(settings, "EMAIL_SUBJECT_PREFIX", "")).strip()
    notification = enqueue_notification(
        recipient=recovery.user,
        event_type=Notification.EventType.PASSWORD_RECOVERY,
        target_type="AccountRecoveryRequest",
        target_id=str(recovery.id),
        subject=f"{prefix} Recover your GradSync account".strip(),
        action_path=path,
        delivery_policy=Notification.DeliveryPolicy.EMAIL_ONLY,
    )
    notification = _safe_delivery(
        notification=notification,
        recipient_email=recovery.requested_email_snapshot,
        body=(
            f"Use this GradSync recovery link once within "
            f"{settings.ACCOUNT_RECOVERY_TOKEN_TTL_SECONDS // 60} minutes:\n{url}"
        ),
    )
    recovery.delivery_notification = notification
    recovery.save(update_fields=["delivery_notification", "updated_at"])
    return notification


@transaction.atomic
def consume_password_recovery(*, request_id, raw_token: str, new_password: str):
    try:
        recovery = (
            AccountRecoveryRequest.objects.select_for_update()
            .select_related("user")
            .get(pk=request_id)
        )
    except (AccountRecoveryRequest.DoesNotExist, ValueError) as exc:
        raise ValueError("Recovery instruction is invalid or expired.") from exc
    expected = _hash_secret(raw_token, "password-recovery")
    if not recovery.is_usable() or not hmac.compare_digest(recovery.token_hash, expected):
        if (
            recovery.status == AccountRecoveryRequest.Status.PENDING
            and recovery.expires_at < timezone.now()
        ):
            recovery.status = AccountRecoveryRequest.Status.EXPIRED
            recovery.save(update_fields=["status", "updated_at"])
        raise ValueError("Recovery instruction is invalid or expired.")

    validate_collaboration_password(new_password)
    user = User.objects.select_for_update().get(pk=recovery.user_id)
    user.set_password(new_password)
    user.save(update_fields=["password"])
    now = timezone.now()
    recovery.status = AccountRecoveryRequest.Status.CONSUMED
    recovery.consumed_at = now
    recovery.save(update_fields=["status", "consumed_at", "updated_at"])
    AccountRecoveryRequest.objects.filter(
        user=user, status=AccountRecoveryRequest.Status.PENDING
    ).exclude(pk=recovery.pk).update(
        status=AccountRecoveryRequest.Status.REVOKED,
        revoked_at=now,
        updated_at=now,
    )
    revoke_user_sessions(user=user, reason="password_recovery")
    record_event(
        None,
        None,
        "account_security.password_recovery_completed",
        "Password recovery completed",
        recovery,
        category=AuditEvent.Category.ACCOUNT_SECURITY,
        target_snapshot={"status": recovery.status, "userId": user.id},
        allowed_snapshot_keys={"status", "userId"},
    )
    return user


@transaction.atomic
def issue_email_change(
    *, user, new_email: str, current_password: str
) -> tuple[EmailChangeRequest, str]:
    user = User.objects.select_for_update().get(pk=user.pk)
    new_email = User.objects.normalize_email(new_email).lower()
    if not user.check_password(current_password):
        raise ValidationError("Current password is incorrect.")
    if new_email == user.email.lower():
        raise ValidationError("New email must be different from the current email.")
    if User.objects.filter(email__iexact=new_email).exclude(pk=user.pk).exists():
        raise ValidationError("An account with this email already exists.")
    now = timezone.now()
    EmailChangeRequest.objects.filter(user=user, status=EmailChangeRequest.Status.PENDING).update(
        status=EmailChangeRequest.Status.SUPERSEDED, updated_at=now
    )
    code = f"{secrets.randbelow(1_000_000):06d}"
    try:
        change = EmailChangeRequest.objects.create(
            user=user,
            previous_email=user.email,
            new_email=new_email,
            verification_hash=_hash_secret(code, "email-change"),
            expires_at=now + timedelta(seconds=settings.EMAIL_CHANGE_TOKEN_TTL_SECONDS),
        )
    except IntegrityError as exc:
        raise ValidationError("This email change is already pending.") from exc
    record_event(
        None,
        user,
        "account_security.email_change_requested",
        "Email change requested",
        change,
        category=AuditEvent.Category.ACCOUNT_SECURITY,
        outcome=AuditEvent.Outcome.QUEUED,
        target_snapshot={"status": change.status},
        allowed_snapshot_keys={"status"},
    )
    return change, code


def _security_notification(
    *,
    change: EmailChangeRequest,
    subject: str,
    recipient_email: str,
    body: str,
) -> Notification:
    notification = enqueue_notification(
        recipient=change.user,
        event_type=Notification.EventType.EMAIL_CHANGE_SECURITY,
        target_type="EmailChangeRequest",
        target_id=str(change.id),
        subject=subject,
        action_path="/profile",
        delivery_policy=Notification.DeliveryPolicy.EMAIL_ONLY,
    )
    return _safe_delivery(notification=notification, recipient_email=recipient_email, body=body)


def deliver_email_change(change: EmailChangeRequest, code: str) -> None:
    prefix = str(getattr(settings, "EMAIL_SUBJECT_PREFIX", "")).strip()
    security = _security_notification(
        change=change,
        subject=f"{prefix} GradSync email change requested".strip(),
        recipient_email=change.previous_email,
        body=(
            f"A change from {change.previous_email} to {change.new_email} was requested. "
            "Your current email remains active until verification."
        ),
    )
    verification = _security_notification(
        change=change,
        subject=f"{prefix} Verify your new GradSync email".strip(),
        recipient_email=change.new_email,
        body=(
            f"Your GradSync email-change code is {code}. It expires in "
            f"{settings.EMAIL_CHANGE_TOKEN_TTL_SECONDS // 60} minutes."
        ),
    )
    EmailChangeRequest.objects.filter(pk=change.pk).update(
        delivery_notification=verification,
        security_notification=security,
    )


@transaction.atomic
def resend_email_change(*, user) -> tuple[EmailChangeRequest, str]:
    change = (
        EmailChangeRequest.objects.select_for_update()
        .filter(user=user, status=EmailChangeRequest.Status.PENDING)
        .order_by("-created_at")
        .first()
    )
    if change is None or not change.is_usable():
        raise ValidationError("No active email change request exists.")
    code = f"{secrets.randbelow(1_000_000):06d}"
    change.verification_hash = _hash_secret(code, "email-change")
    change.save(update_fields=["verification_hash", "updated_at"])
    return change, code


@transaction.atomic
def cancel_email_change(*, user) -> EmailChangeRequest | None:
    change = (
        EmailChangeRequest.objects.select_for_update()
        .filter(user=user, status=EmailChangeRequest.Status.PENDING)
        .order_by("-created_at")
        .first()
    )
    if change is None:
        return None
    change.status = EmailChangeRequest.Status.CANCELLED
    change.cancelled_at = timezone.now()
    change.save(update_fields=["status", "cancelled_at", "updated_at"])
    record_event(
        None,
        user,
        "account_security.email_change_cancelled",
        "Email change cancelled",
        change,
        category=AuditEvent.Category.ACCOUNT_SECURITY,
        target_snapshot={"status": change.status},
        allowed_snapshot_keys={"status"},
    )
    return change


@transaction.atomic
def verify_email_change(*, user, request_id, code: str):
    try:
        change = EmailChangeRequest.objects.select_for_update().get(pk=request_id, user=user)
    except (EmailChangeRequest.DoesNotExist, ValueError) as exc:
        raise ValueError("Email change instruction is invalid or expired.") from exc
    if not change.is_usable() or not hmac.compare_digest(
        change.verification_hash, _hash_secret(code, "email-change")
    ):
        raise ValueError("Email change instruction is invalid or expired.")
    locked_user = User.objects.select_for_update().get(pk=user.pk)
    if User.objects.filter(email__iexact=change.new_email).exclude(pk=locked_user.pk).exists():
        raise ValidationError("An account with this email already exists.")
    previous_email = locked_user.email
    locked_user.email = change.new_email
    locked_user.email_verified_at = timezone.now()
    locked_user.save(update_fields=["email", "email_verified_at"])
    change.status = EmailChangeRequest.Status.VERIFIED
    change.verified_at = timezone.now()
    change.save(update_fields=["status", "verified_at", "updated_at"])
    revoke_user_sessions(user=locked_user, actor=locked_user, reason="email_changed")
    record_event(
        None,
        locked_user,
        "account_security.email_change_completed",
        "Email change completed",
        change,
        category=AuditEvent.Category.ACCOUNT_SECURITY,
        target_snapshot={"status": change.status},
        allowed_snapshot_keys={"status"},
    )
    subject_prefix = getattr(settings, "EMAIL_SUBJECT_PREFIX", "")
    for recipient in (previous_email, locked_user.email):
        _security_notification(
            change=change,
            subject=f"{subject_prefix} GradSync email changed".strip(),
            recipient_email=recipient,
            body="Your GradSync sign-in email change is complete.",
        )
    return locked_user


def pending_email_change(user) -> EmailChangeRequest | None:
    change = (
        EmailChangeRequest.objects.filter(user=user, status=EmailChangeRequest.Status.PENDING)
        .select_related("delivery_notification")
        .order_by("-created_at")
        .first()
    )
    if change and change.expires_at < timezone.now():
        EmailChangeRequest.objects.filter(pk=change.pk).update(
            status=EmailChangeRequest.Status.EXPIRED
        )
        return None
    return change
