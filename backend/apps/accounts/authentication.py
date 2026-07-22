from rest_framework.exceptions import AuthenticationFailed
from rest_framework_simplejwt.authentication import JWTAuthentication

from .models import User


class ActiveAccountJWTAuthentication(JWTAuthentication):
    """Authenticate Bearer tokens and reject accounts disabled after issuance."""

    def get_user(self, validated_token):
        user = super().get_user(validated_token)
        if user.status != User.Status.ACTIVE:
            raise AuthenticationFailed("This account is not active.", code="user_inactive")
        return user
