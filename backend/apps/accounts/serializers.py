from django.contrib.auth import authenticate
from drf_spectacular.utils import extend_schema_field
from rest_framework import serializers

from .models import AccountSession, EmailChangeRequest, RoleActivationRequest, User


class UserSerializer(serializers.ModelSerializer):
    degreeType = serializers.SerializerMethodField()

    class Meta:
        model = User
        fields = [
            "id",
            "email",
            "name",
            "nickname",
            "global_role",
            "requested_role",
            "active_role",
            "status",
            "locale",
            "degreeType",
        ]

    @extend_schema_field(serializers.CharField(allow_null=True))
    def get_degreeType(self, obj):
        profile = getattr(obj, "student_profile", None)
        return profile.degree_type if profile else None


class AuthenticatedUserSerializer(UserSerializer):
    accessToken = serializers.CharField(read_only=True)
    accessTokenExpiresAt = serializers.DateTimeField(read_only=True)

    class Meta(UserSerializer.Meta):
        fields = [*UserSerializer.Meta.fields, "accessToken", "accessTokenExpiresAt"]


class AccessTokenSerializer(serializers.Serializer):
    accessToken = serializers.CharField(read_only=True)
    accessTokenExpiresAt = serializers.DateTimeField(read_only=True)


class PasswordRecoveryRequestSerializer(serializers.Serializer):
    email = serializers.EmailField(max_length=254)
    returnTo = serializers.CharField(max_length=255, required=False, default="/reset-password")

    def validate_returnTo(self, value):
        if not value.startswith("/") or value.startswith("//"):
            raise serializers.ValidationError("Return path is not allowed.")
        return value


class PasswordRecoveryConfirmSerializer(serializers.Serializer):
    requestId = serializers.UUIDField()
    token = serializers.CharField(min_length=32, max_length=512, trim_whitespace=False)
    newPassword = serializers.CharField(
        min_length=10, max_length=256, trim_whitespace=False, write_only=True
    )


class EmailChangeRequestSerializer(serializers.Serializer):
    newEmail = serializers.EmailField(max_length=254)
    currentPassword = serializers.CharField(max_length=256, trim_whitespace=False, write_only=True)


class EmailChangeVerifySerializer(serializers.Serializer):
    requestId = serializers.UUIDField()
    code = serializers.CharField(min_length=6, max_length=64, trim_whitespace=True)


def mask_email(value: str) -> str:
    local, separator, domain = value.partition("@")
    if not separator:
        return "***"
    visible = local[:1]
    return f"{visible}{'*' * max(2, len(local) - 1)}@{domain}"


class EmailChangeStateSerializer(serializers.ModelSerializer):
    pending = serializers.SerializerMethodField()
    requestId = serializers.UUIDField(source="id", read_only=True)
    maskedNewEmail = serializers.SerializerMethodField()
    expiresAt = serializers.DateTimeField(source="expires_at", read_only=True)
    deliveryStatus = serializers.SerializerMethodField()

    class Meta:
        model = EmailChangeRequest
        fields = [
            "pending",
            "requestId",
            "maskedNewEmail",
            "status",
            "expiresAt",
            "deliveryStatus",
        ]

    def get_pending(self, obj):
        return obj.status == EmailChangeRequest.Status.PENDING

    def get_maskedNewEmail(self, obj):
        return mask_email(obj.new_email)

    def get_deliveryStatus(self, obj):
        notification = obj.delivery_notification
        return notification.status if notification else None


class AccountSessionSerializer(serializers.ModelSerializer):
    current = serializers.SerializerMethodField()
    deviceLabel = serializers.CharField(source="device_label", read_only=True)
    createdAt = serializers.DateTimeField(source="created_at", read_only=True)
    lastSeenAt = serializers.DateTimeField(source="last_seen_at", read_only=True)
    expiresAt = serializers.DateTimeField(source="expires_at", read_only=True)
    revokedAt = serializers.DateTimeField(source="revoked_at", read_only=True)

    class Meta:
        model = AccountSession
        fields = [
            "id",
            "status",
            "current",
            "deviceLabel",
            "createdAt",
            "lastSeenAt",
            "expiresAt",
            "revokedAt",
        ]

    def get_current(self, obj):
        return str(obj.id) == str(self.context.get("current_session_id") or "")


class LoginSerializer(serializers.Serializer):
    email = serializers.EmailField()
    password = serializers.CharField(write_only=True, trim_whitespace=False)

    default_error_messages = {
        "invalid_credentials": "Invalid email or password.",
        "inactive_account": "This account is not active. Contact an administrator.",
    }

    def validate(self, attrs):
        request = self.context.get("request")
        user = authenticate(request, email=attrs["email"], password=attrs["password"])
        if user is None:
            # Generic message: never reveal whether the email exists.
            self.fail("invalid_credentials")
        if user.status != User.Status.ACTIVE:
            self.fail("inactive_account")
        attrs["user"] = user
        return attrs


# ── Admin account management ──


class AccountUpdateSerializer(serializers.Serializer):
    name = serializers.CharField(max_length=255, required=False)
    global_role = serializers.ChoiceField(choices=["admin", "advisor", "student"], required=False)

    def validate(self, attrs):
        if not attrs:
            raise serializers.ValidationError("At least one field must be provided.")
        return attrs


class LocalePreferenceSerializer(serializers.Serializer):
    locale = serializers.ChoiceField(choices=["en", "zh"])
    updatedAt = serializers.DateTimeField(source="updated_at", read_only=True, required=False)


class RegistrationSerializer(serializers.Serializer):
    email = serializers.EmailField()
    password = serializers.CharField(write_only=True, trim_whitespace=False)
    name = serializers.CharField(max_length=255)
    nickname = serializers.CharField(max_length=80)
    requestedRole = serializers.ChoiceField(choices=["student", "teacher"])
    degreeType = serializers.ChoiceField(
        choices=["masters", "doctoral"],
        required=False,
        allow_null=True,
        allow_blank=True,
    )


class EmailVerificationSerializer(serializers.Serializer):
    email = serializers.EmailField()
    code = serializers.CharField(max_length=12)


class VerificationResendSerializer(serializers.Serializer):
    email = serializers.EmailField()


class ProfileUpdateSerializer(serializers.Serializer):
    name = serializers.CharField(max_length=255)
    nickname = serializers.CharField(max_length=80)
    degreeType = serializers.ChoiceField(
        choices=["masters", "doctoral"], required=False, allow_null=True
    )


class PasswordChangeSerializer(serializers.Serializer):
    currentPassword = serializers.CharField(write_only=True, trim_whitespace=False)
    newPassword = serializers.CharField(write_only=True, trim_whitespace=False)


class RoleActivationSerializer(serializers.ModelSerializer):
    user = UserSerializer(read_only=True)
    reviewer = UserSerializer(read_only=True)
    requestedRole = serializers.CharField(source="requested_role", read_only=True)
    activationSource = serializers.CharField(source="activation_source", read_only=True)
    reviewReason = serializers.CharField(source="review_reason", read_only=True)
    reviewedAt = serializers.DateTimeField(source="reviewed_at", read_only=True)
    createdAt = serializers.DateTimeField(source="created_at", read_only=True)

    class Meta:
        model = RoleActivationRequest
        fields = [
            "id",
            "user",
            "requestedRole",
            "activationSource",
            "status",
            "reviewer",
            "reviewReason",
            "reviewedAt",
            "createdAt",
        ]


class RoleActivationUpdateSerializer(serializers.Serializer):
    action = serializers.ChoiceField(choices=["approve", "reject", "revoke", "expire"])
    reason = serializers.CharField(max_length=1000, required=False, allow_blank=True)

    def validate(self, attrs):
        attrs["reason"] = attrs.get("reason", "").strip()
        if attrs["action"] in {"reject", "revoke"} and not attrs["reason"]:
            raise serializers.ValidationError(
                {"reason": "A reason is required for rejection or revocation."}
            )
        return attrs


class StudentOptionSerializer(serializers.ModelSerializer):
    degreeType = serializers.SerializerMethodField()
    label = serializers.SerializerMethodField()
    eligibility = serializers.SerializerMethodField()

    class Meta:
        model = User
        fields = ["id", "nickname", "email", "degreeType", "label", "eligibility"]

    @extend_schema_field(serializers.CharField(allow_null=True))
    def get_degreeType(self, obj):
        profile = getattr(obj, "student_profile", None)
        return profile.degree_type if profile else None

    @extend_schema_field(serializers.CharField())
    def get_label(self, obj):
        nickname = obj.nickname or obj.name
        return f"{nickname} <{obj.email}>"

    @extend_schema_field(serializers.DictField())
    def get_eligibility(self, obj):
        project_id = self.context.get("project_id")
        if not project_id:
            return {"selectable": True, "reason": ""}
        active_membership_exists = obj.project_memberships.filter(
            project_id=project_id,
            status="active",
        ).exists()
        if active_membership_exists:
            return {"selectable": False, "reason": "already_active_member"}
        return {"selectable": True, "reason": ""}
