from django.contrib.auth import authenticate
from drf_spectacular.utils import extend_schema_field
from rest_framework import serializers

from .models import RoleActivationRequest, User


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


class AccountCreateSerializer(serializers.Serializer):
    email = serializers.EmailField()
    name = serializers.CharField(max_length=255)
    global_role = serializers.ChoiceField(choices=["advisor", "student"])

    def validate_email(self, value):
        if User.objects.filter(email=value).exists():
            raise serializers.ValidationError("An account with this email already exists.")
        return value


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
    nickname = serializers.CharField(max_length=80)
    requestedRole = serializers.ChoiceField(choices=["student", "teacher", "administrator"])
    degreeType = serializers.ChoiceField(
        choices=["masters", "doctoral"],
        required=False,
        allow_null=True,
        allow_blank=True,
    )


class EmailVerificationSerializer(serializers.Serializer):
    email = serializers.EmailField()
    code = serializers.CharField(max_length=12)


class NicknameUpdateSerializer(serializers.Serializer):
    nickname = serializers.CharField(max_length=80)


class RoleActivationSerializer(serializers.ModelSerializer):
    user = UserSerializer(read_only=True)
    requestedRole = serializers.CharField(source="requested_role", read_only=True)
    activationSource = serializers.CharField(source="activation_source", read_only=True)
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
            "reviewedAt",
            "createdAt",
        ]


class RoleActivationUpdateSerializer(serializers.Serializer):
    action = serializers.ChoiceField(choices=["approve", "reject", "revoke", "expire"])


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
