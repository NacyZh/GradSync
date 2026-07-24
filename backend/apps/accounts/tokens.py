from datetime import UTC, datetime

from django.conf import settings
from django.contrib.auth import get_user_model
from rest_framework.exceptions import AuthenticationFailed
from rest_framework_simplejwt.exceptions import TokenError
from rest_framework_simplejwt.settings import api_settings
from rest_framework_simplejwt.tokens import RefreshToken

from .models import AccountSession
from .session_services import get_active_session, touch_session


def issue_token_pair(user, account_session: AccountSession):
    refresh = RefreshToken.for_user(user)
    refresh["sid"] = str(account_session.id)
    return _token_payload(refresh), str(refresh)


def rotate_refresh_token(raw_refresh: str):
    try:
        refresh = RefreshToken(raw_refresh)
        user = get_user_model().objects.get(pk=refresh[api_settings.USER_ID_CLAIM])
        sid = refresh["sid"]
    except (TokenError, get_user_model().DoesNotExist, KeyError) as exc:
        raise AuthenticationFailed("Refresh token is invalid or expired.") from exc

    if user.status != user.Status.ACTIVE:
        raise AuthenticationFailed("This account is not active.")
    try:
        account_session = get_active_session(user=user, session_id=sid)
    except (AccountSession.DoesNotExist, ValueError) as exc:
        raise AuthenticationFailed("Session is invalid or expired.") from exc

    refresh.blacklist()
    replacement = RefreshToken.for_user(user)
    replacement["sid"] = str(account_session.id)
    touch_session(account_session)
    return _token_payload(replacement), str(replacement)


def revoke_refresh_token(raw_refresh: str | None) -> None:
    if not raw_refresh:
        return
    try:
        RefreshToken(raw_refresh).blacklist()
    except TokenError:
        pass


def set_refresh_cookie(response, refresh_token: str) -> None:
    response.set_cookie(
        settings.JWT_REFRESH_COOKIE_NAME,
        refresh_token,
        max_age=int(settings.SIMPLE_JWT["REFRESH_TOKEN_LIFETIME"].total_seconds()),
        path=settings.JWT_REFRESH_COOKIE_PATH,
        secure=settings.JWT_REFRESH_COOKIE_SECURE,
        httponly=True,
        samesite=settings.JWT_REFRESH_COOKIE_SAMESITE,
    )


def clear_refresh_cookie(response) -> None:
    response.delete_cookie(
        settings.JWT_REFRESH_COOKIE_NAME,
        path=settings.JWT_REFRESH_COOKIE_PATH,
        samesite=settings.JWT_REFRESH_COOKIE_SAMESITE,
    )


def refresh_cookie(request) -> str | None:
    return request.COOKIES.get(settings.JWT_REFRESH_COOKIE_NAME)


def _token_payload(refresh: RefreshToken) -> dict[str, str]:
    access = refresh.access_token
    expires_at = datetime.fromtimestamp(access["exp"], tz=UTC)
    return {
        "accessToken": str(access),
        "accessTokenExpiresAt": expires_at.isoformat().replace("+00:00", "Z"),
    }
