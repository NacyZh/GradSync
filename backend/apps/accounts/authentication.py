from rest_framework.authentication import SessionAuthentication
from rest_framework.exceptions import AuthenticationFailed
from rest_framework_simplejwt.authentication import JWTAuthentication

from .models import AccountSession, User
from .session_services import get_active_session, touch_session


class ActiveAccountJWTAuthentication(JWTAuthentication):
    """Authenticate Bearer tokens and reject accounts disabled after issuance."""

    def get_user(self, validated_token):
        user = super().get_user(validated_token)
        if user.status != User.Status.ACTIVE:
            raise AuthenticationFailed("This account is not active.", code="user_inactive")
        sid = validated_token.get("sid")
        if not sid:
            raise AuthenticationFailed("Session is invalid or expired.", code="session_invalid")
        try:
            session = get_active_session(user=user, session_id=sid)
        except (AccountSession.DoesNotExist, ValueError) as exc:
            raise AuthenticationFailed(
                "Session is invalid or expired.", code="session_invalid"
            ) from exc
        touch_session(session)
        return user


class ActiveAccountSessionAuthentication(SessionAuthentication):
    """Reject revoked or unbound Django sessions on their next protected request."""

    def authenticate(self, request):
        result = super().authenticate(request)
        if result is None:
            return None
        user, auth = result
        if user.status != User.Status.ACTIVE:
            raise AuthenticationFailed("This account is not active.", code="user_inactive")
        sid = request.session.get("account_session_id")
        if not sid:
            raise AuthenticationFailed("Session is invalid or expired.", code="session_invalid")
        try:
            session = get_active_session(user=user, session_id=sid)
        except (AccountSession.DoesNotExist, ValueError) as exc:
            raise AuthenticationFailed(
                "Session is invalid or expired.", code="session_invalid"
            ) from exc
        touch_session(session, request)
        return user, auth
