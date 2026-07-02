from django.contrib.auth import authenticate
from rest_framework import serializers

from .models import User


class UserSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = ["id", "email", "name", "global_role", "status", "locale"]


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
