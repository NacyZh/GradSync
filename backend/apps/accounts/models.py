import uuid

from django.conf import settings
from django.contrib.auth.models import AbstractUser
from django.db import models
from django.utils import timezone

from .managers import UserManager


class User(AbstractUser):
    class GlobalRole(models.TextChoices):
        ADVISOR = "advisor", "Advisor"
        STUDENT = "student", "Student"
        ADMIN = "admin", "Administrator"

    class Status(models.TextChoices):
        INVITED = "invited", "Invited"
        PENDING_EMAIL_VERIFICATION = "pending_email_verification", "Pending email verification"
        PENDING_ROLE_ACTIVATION = "pending_role_activation", "Pending role activation"
        ACTIVE = "active", "Active"
        SUSPENDED = "suspended", "Suspended"
        ARCHIVED = "archived", "Archived"

    class RequestedRole(models.TextChoices):
        STUDENT = "student", "Student"
        TEACHER = "teacher", "Teacher"
        ADMINISTRATOR = "administrator", "Administrator"
        PENDING = "pending", "Pending"

    username = None
    email = models.EmailField(unique=True)
    name = models.CharField(max_length=255)
    global_role = models.CharField(
        max_length=20, choices=GlobalRole.choices, default=GlobalRole.STUDENT
    )
    status = models.CharField(max_length=30, choices=Status.choices, default=Status.ACTIVE)
    locale = models.CharField(max_length=5, default="en")
    requested_role = models.CharField(
        max_length=30, choices=RequestedRole.choices, default=RequestedRole.STUDENT
    )
    active_role = models.CharField(
        max_length=30, choices=RequestedRole.choices, default=RequestedRole.STUDENT
    )
    nickname = models.CharField(max_length=80, blank=True)
    email_verified_at = models.DateTimeField(null=True, blank=True)

    USERNAME_FIELD = "email"
    REQUIRED_FIELDS = ["name"]

    objects = UserManager()

    def __str__(self) -> str:
        return self.email

    @property
    def is_advisor(self) -> bool:
        return self.global_role in {self.GlobalRole.ADVISOR, self.GlobalRole.ADMIN}

    @property
    def is_administrator(self) -> bool:
        return self.global_role == self.GlobalRole.ADMIN


class StudentProfile(models.Model):
    class DegreeType(models.TextChoices):
        MASTERS = "masters", "Masters"
        DOCTORAL = "doctoral", "Doctoral"

    user = models.OneToOneField(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="student_profile"
    )
    degree_type = models.CharField(max_length=20, choices=DegreeType.choices)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)


class TeacherProfile(models.Model):
    user = models.OneToOneField(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="teacher_profile"
    )
    approved_at = models.DateTimeField()
    approved_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="approved_teacher_profiles",
    )


class EmailVerificationCode(models.Model):
    class Purpose(models.TextChoices):
        REGISTRATION = "registration", "Registration"
        EMAIL_CHANGE = "email_change", "Email change"

    class Status(models.TextChoices):
        PENDING = "pending", "Pending"
        CONSUMED = "consumed", "Consumed"
        EXPIRED = "expired", "Expired"
        REVOKED = "revoked", "Revoked"

    email = models.EmailField(db_index=True)
    purpose = models.CharField(max_length=30, choices=Purpose.choices, default=Purpose.REGISTRATION)
    code_hash = models.CharField(max_length=128)
    plain_code = models.CharField(max_length=12, blank=True)
    status = models.CharField(max_length=20, choices=Status.choices, default=Status.PENDING)
    expires_at = models.DateTimeField()
    consumed_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def is_usable(self) -> bool:
        return self.status == self.Status.PENDING and self.expires_at >= timezone.now()


class RoleActivationRequest(models.Model):
    class RequestedRole(models.TextChoices):
        TEACHER = "teacher", "Teacher"
        ADMINISTRATOR = "administrator", "Administrator"

    class ActivationSource(models.TextChoices):
        ADMIN_APPROVAL = "administrator_approval", "Administrator approval"
        INVITATION = "invitation", "Invitation"

    class Status(models.TextChoices):
        PENDING = "pending", "Pending"
        APPROVED = "approved", "Approved"
        REJECTED = "rejected", "Rejected"
        EXPIRED = "expired", "Expired"
        REVOKED = "revoked", "Revoked"

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="role_activation_requests"
    )
    requested_role = models.CharField(max_length=30, choices=RequestedRole.choices)
    activation_source = models.CharField(
        max_length=40,
        choices=ActivationSource.choices,
        default=ActivationSource.ADMIN_APPROVAL,
    )
    status = models.CharField(max_length=20, choices=Status.choices, default=Status.PENDING)
    reviewer = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="reviewed_role_activation_requests",
    )
    invitation_token_hash = models.CharField(max_length=128, blank=True)
    expires_at = models.DateTimeField(null=True, blank=True)
    reviewed_at = models.DateTimeField(null=True, blank=True)
    review_reason = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-created_at"]


class AccountRecoveryRequest(models.Model):
    class Status(models.TextChoices):
        PENDING = "pending", "Pending"
        CONSUMED = "consumed", "Consumed"
        SUPERSEDED = "superseded", "Superseded"
        EXPIRED = "expired", "Expired"
        REVOKED = "revoked", "Revoked"

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name="recovery_requests",
    )
    token_hash = models.CharField(max_length=64, unique=True)
    status = models.CharField(max_length=20, choices=Status.choices, default=Status.PENDING)
    requested_email_snapshot = models.EmailField()
    requested_ip_hash = models.CharField(max_length=64, blank=True)
    requested_user_agent = models.CharField(max_length=255, blank=True)
    expires_at = models.DateTimeField()
    consumed_at = models.DateTimeField(null=True, blank=True)
    superseded_at = models.DateTimeField(null=True, blank=True)
    revoked_at = models.DateTimeField(null=True, blank=True)
    delivery_notification = models.ForeignKey(
        "notifications.Notification",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="recovery_requests",
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        indexes = [
            models.Index(
                fields=["user", "status", "-created_at"], name="account_recovery_user_idx"
            ),
            models.Index(fields=["status", "expires_at"], name="account_recovery_expiry_idx"),
        ]
        constraints = [
            models.UniqueConstraint(
                fields=["user"],
                condition=models.Q(status="pending"),
                name="unique_pending_account_recovery",
            )
        ]

    def is_usable(self) -> bool:
        return self.status == self.Status.PENDING and self.expires_at >= timezone.now()


class EmailChangeRequest(models.Model):
    class Status(models.TextChoices):
        PENDING = "pending", "Pending"
        VERIFIED = "verified", "Verified"
        CANCELLED = "cancelled", "Cancelled"
        SUPERSEDED = "superseded", "Superseded"
        EXPIRED = "expired", "Expired"

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name="email_change_requests",
    )
    previous_email = models.EmailField()
    new_email = models.EmailField()
    verification_hash = models.CharField(max_length=64, unique=True)
    status = models.CharField(max_length=20, choices=Status.choices, default=Status.PENDING)
    expires_at = models.DateTimeField()
    verified_at = models.DateTimeField(null=True, blank=True)
    cancelled_at = models.DateTimeField(null=True, blank=True)
    delivery_notification = models.ForeignKey(
        "notifications.Notification",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="email_change_deliveries",
    )
    security_notification = models.ForeignKey(
        "notifications.Notification",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="email_change_security_notices",
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        indexes = [
            models.Index(fields=["user", "status", "-created_at"], name="email_change_user_idx"),
            models.Index(fields=["new_email", "status"], name="email_change_address_idx"),
        ]
        constraints = [
            models.UniqueConstraint(
                fields=["user"],
                condition=models.Q(status="pending"),
                name="unique_pending_email_change_user",
            ),
            models.UniqueConstraint(
                fields=["new_email"],
                condition=models.Q(status="pending"),
                name="unique_pending_email_change_address",
            ),
            models.CheckConstraint(
                condition=~models.Q(previous_email=models.F("new_email")),
                name="email_change_addresses_differ",
            ),
        ]

    def is_usable(self) -> bool:
        return self.status == self.Status.PENDING and self.expires_at >= timezone.now()


class AccountSession(models.Model):
    class Status(models.TextChoices):
        ACTIVE = "active", "Active"
        REVOKED = "revoked", "Revoked"
        EXPIRED = "expired", "Expired"

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="account_sessions",
    )
    django_session_key_hash = models.CharField(max_length=64, unique=True, null=True, blank=True)
    status = models.CharField(max_length=20, choices=Status.choices, default=Status.ACTIVE)
    device_label = models.CharField(max_length=120, default="Unknown device")
    user_agent = models.CharField(max_length=255, blank=True)
    initial_ip_hash = models.CharField(max_length=64, blank=True)
    last_ip_hash = models.CharField(max_length=64, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    last_seen_at = models.DateTimeField(default=timezone.now)
    expires_at = models.DateTimeField()
    revoked_at = models.DateTimeField(null=True, blank=True)
    revoked_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="revoked_account_sessions",
    )
    revoke_reason = models.CharField(max_length=255, blank=True)

    class Meta:
        indexes = [
            models.Index(
                fields=["user", "status", "-last_seen_at"], name="account_session_user_idx"
            ),
            models.Index(fields=["status", "expires_at"], name="account_session_expiry_idx"),
        ]

    @staticmethod
    def default_expiry():
        from datetime import timedelta

        return timezone.now() + timedelta(
            seconds=int(settings.SIMPLE_JWT["REFRESH_TOKEN_LIFETIME"].total_seconds())
        )

    def is_active_session(self) -> bool:
        return self.status == self.Status.ACTIVE and self.expires_at > timezone.now()
