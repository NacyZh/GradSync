from django.contrib.auth import authenticate
from rest_framework import serializers

from .models import User


class UserSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = ["id", "email", "name", "global_role", "status"]


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
