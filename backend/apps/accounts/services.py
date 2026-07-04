import hashlib
import secrets

from django.conf import settings
from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError
from django.core.mail import send_mail
from django.db import transaction
from django.utils import timezone

from apps.audit.services import record_role_activation
from apps.notifications.models import Notification
from apps.notifications.services import (
    enqueue_notification,
    mark_notification_attempt_failed,
    mark_notification_status,
)

from .models import EmailVerificationCode, RoleActivationRequest, StudentProfile, TeacherProfile

User = get_user_model()


class AccountsService:
    """Account provisioning and lifecycle management.

    Only administrators may invoke these operations (enforced at the view layer
    via IsAdministrator permission).
    """

    @staticmethod
    def create_account(*, email: str, name: str, global_role: str, created_by) -> User:
        if User.objects.filter(email=email).exists():
            raise ValidationError("An account with this email already exists.")

        user = User.objects.create(
            email=email,
            name=name,
            global_role=global_role,
            status=User.Status.INVITED,
            is_active=True,
        )
        user.set_unusable_password()
        user.save(update_fields=["password"])
        return user

    @staticmethod
    def edit_account(*, user: User, name: str | None, global_role: str | None) -> User:
        if name is not None:
            user.name = name
        if global_role is not None:
            _guard_last_admin(user, new_role=global_role)
            user.global_role = global_role
        user.save(update_fields=["name", "global_role"])
        return user

    @staticmethod
    def suspend_account(*, user: User, actor) -> User:
        _guard_last_admin(user, new_role=None)
        user.status = User.Status.SUSPENDED
        user.is_active = False
        user.save(update_fields=["status", "is_active"])
        return user

    @staticmethod
    def reactivate_account(*, user: User) -> User:
        user.status = User.Status.ACTIVE
        user.is_active = True
        user.save(update_fields=["status", "is_active"])
        return user

    @staticmethod
    def archive_account(*, user: User, actor) -> User:
        _guard_last_admin(user, new_role=None)
        user.status = User.Status.ARCHIVED
        user.is_active = False
        user.save(update_fields=["status", "is_active"])
        return user


def _guard_last_admin(user: User, new_role: str | None):
    """Prevent the last active administrator from being demoted, suspended, or archived.

    Called before any role change, suspend, or archive action on an admin account.
    When `new_role` is None the action is a status change (suspend/archive), not a role change.
    """
    if not user.is_administrator:
        return  # Target is not an admin — no restriction.

    # If the action changes the role to non-admin, it's a demotion.
    would_lose_admin_role = new_role is not None and new_role != User.GlobalRole.ADMIN
    # If new_role is None, this is a suspend/archive — admin role is preserved
    # but the account becomes inactive.
    would_lose_active_admin = new_role is None

    if would_lose_admin_role or would_lose_active_admin:
        active_admin_count = User.objects.filter(
            global_role=User.GlobalRole.ADMIN, status=User.Status.ACTIVE
        ).count()
        if active_admin_count <= 1:
            raise ValidationError(
                "Cannot remove, demote, suspend, or archive the last active administrator. "
                "Promote another user to administrator first."
            )


def validate_collaboration_password(password: str):
    errors = []
    if len(password or "") < 8:
        errors.append("at least 8 characters")
    if not any(char.islower() for char in password or ""):
        errors.append("one lowercase letter")
    if not any(char.isupper() for char in password or ""):
        errors.append("one uppercase letter")
    if not any(char.isdigit() for char in password or ""):
        errors.append("one digit")
    if not any(not char.isalnum() for char in password or ""):
        errors.append("one non-alphanumeric character")
    if errors:
        raise ValidationError("Password must contain " + ", ".join(errors) + ".")


def _hash_code(code: str) -> str:
    return hashlib.sha256(code.encode("utf-8")).hexdigest()


def _role_to_global_role(role: str) -> str:
    if role == "teacher":
        return User.GlobalRole.ADVISOR
    if role == "administrator":
        return User.GlobalRole.ADMIN
    return User.GlobalRole.STUDENT


@transaction.atomic
def register_account(*, email: str, password: str, nickname: str, requested_role: str, degree_type: str | None):
    if User.objects.filter(email=email).exists():
        raise ValidationError("An account with this email already exists.")
    if requested_role not in {"student", "teacher", "administrator"}:
        raise ValidationError("Requested role must be student, teacher, or administrator.")
    if requested_role == "student" and degree_type not in {"masters", "doctoral"}:
        raise ValidationError("Student registration requires a masters or doctoral degree type.")
    validate_collaboration_password(password)
    nickname = (nickname or "").strip()
    if not nickname:
        raise ValidationError("Nickname is required.")

    user = User.objects.create(
        email=email,
        name=nickname,
        nickname=nickname,
        requested_role=requested_role,
        active_role=User.RequestedRole.PENDING,
        global_role=_role_to_global_role(requested_role),
        status=User.Status.PENDING_EMAIL_VERIFICATION,
        is_active=True,
    )
    user.set_password(password)
    user.save(update_fields=["password"])
    if requested_role == "student":
        StudentProfile.objects.create(user=user, degree_type=degree_type)
    code = create_verification_code(email=email)
    send_verification_email(email=email, code=code.plain_code, user=user, verification=code)
    return user, code


def create_verification_code(*, email: str) -> EmailVerificationCode:
    EmailVerificationCode.objects.filter(
        email=email, purpose=EmailVerificationCode.Purpose.REGISTRATION, status=EmailVerificationCode.Status.PENDING
    ).update(status=EmailVerificationCode.Status.REVOKED)
    code = f"{secrets.randbelow(1000000):06d}"
    return EmailVerificationCode.objects.create(
        email=email,
        purpose=EmailVerificationCode.Purpose.REGISTRATION,
        code_hash=_hash_code(code),
        plain_code=code,
        expires_at=timezone.now()
        + timezone.timedelta(minutes=settings.EMAIL_VERIFICATION_CODE_TTL_MINUTES),
    )


def send_verification_email(*, email: str, code: str, user, verification: EmailVerificationCode):
    notification = enqueue_notification(
        recipient=user,
        event_type=Notification.EventType.VERIFICATION_CODE,
        target_type="EmailVerificationCode",
        target_id=str(verification.id),
        subject="Verify your GradSync email",
        action_path="/verify-email",
    )
    mark_notification_status(notification, Notification.Status.QUEUED)
    try:
        send_mail(
            notification.subject,
            f"Your GradSync verification code is {code}.",
            settings.DEFAULT_FROM_EMAIL,
            [email],
            fail_silently=False,
        )
    except Exception as exc:  # pragma: no cover - covered by integration failure tests
        mark_notification_attempt_failed(notification, exc)
        return notification
    mark_notification_status(notification, Notification.Status.SENT)
    return notification


@transaction.atomic
def verify_email(*, email: str, code: str):
    verification = (
        EmailVerificationCode.objects.select_for_update()
        .filter(email=email, purpose=EmailVerificationCode.Purpose.REGISTRATION)
        .order_by("-created_at")
        .first()
    )
    if verification is None or not verification.is_usable() or verification.code_hash != _hash_code(code):
        raise ValidationError("Invalid or expired verification code.")
    user = User.objects.select_for_update().get(email=email)
    user.email_verified_at = timezone.now()
    if user.requested_role == "student":
        user.active_role = "student"
        user.status = User.Status.ACTIVE
    else:
        user.active_role = User.RequestedRole.PENDING
        user.status = User.Status.PENDING_ROLE_ACTIVATION
        RoleActivationRequest.objects.get_or_create(
            user=user,
            status=RoleActivationRequest.Status.PENDING,
            defaults={
                "requested_role": user.requested_role,
                "expires_at": timezone.now() + timezone.timedelta(days=settings.ROLE_ACTIVATION_TTL_DAYS),
            },
        )
    user.save(update_fields=["email_verified_at", "active_role", "status"])
    verification.status = EmailVerificationCode.Status.CONSUMED
    verification.consumed_at = timezone.now()
    verification.save(update_fields=["status", "consumed_at"])
    return user


@transaction.atomic
def decide_role_activation(*, activation: RoleActivationRequest, reviewer, action: str):
    if action not in {"approve", "reject", "revoke", "expire"}:
        raise ValidationError("Invalid role activation action.")
    activation.reviewer = reviewer
    activation.reviewed_at = timezone.now()
    if action == "approve":
        activation.status = RoleActivationRequest.Status.APPROVED
        user = activation.user
        user.active_role = activation.requested_role
        user.global_role = _role_to_global_role(activation.requested_role)
        user.status = User.Status.ACTIVE
        user.save(update_fields=["active_role", "global_role", "status"])
        if activation.requested_role == "teacher":
            TeacherProfile.objects.update_or_create(
                user=user,
                defaults={"approved_at": timezone.now(), "approved_by": reviewer},
            )
    elif action == "reject":
        activation.status = RoleActivationRequest.Status.REJECTED
    elif action == "revoke":
        activation.status = RoleActivationRequest.Status.REVOKED
    else:
        activation.status = RoleActivationRequest.Status.EXPIRED
    activation.save(update_fields=["status", "reviewer", "reviewed_at"])
    record_role_activation(reviewer, activation, action)
    enqueue_notification(
        recipient=activation.user,
        sender=reviewer,
        event_type=Notification.EventType.ROLE_ACTIVATION,
        target_type="RoleActivationRequest",
        target_id=str(activation.id),
        subject=f"Role activation {activation.status}",
        action_path="/profile",
    )
    return activation


def update_nickname(*, user, nickname: str):
    nickname = (nickname or "").strip()
    if not nickname:
        raise ValidationError("Nickname is required.")
    user.nickname = nickname
    user.name = nickname
    user.save(update_fields=["nickname", "name"])
    return user
