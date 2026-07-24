import hashlib
import re
from datetime import timedelta

from django.conf import settings
from django.contrib.sessions.models import Session
from django.db import transaction
from django.utils import timezone
from rest_framework_simplejwt.token_blacklist.models import BlacklistedToken, OutstandingToken
from rest_framework_simplejwt.tokens import RefreshToken

from .models import AccountSession


def _keyed_hash(value: str) -> str:
    return hashlib.sha256(f"{settings.SECRET_KEY}:{value}".encode()).hexdigest()


def _request_ip(request) -> str:
    forwarded = request.META.get("HTTP_X_FORWARDED_FOR", "")
    return (forwarded.split(",", 1)[0].strip() or request.META.get("REMOTE_ADDR", ""))[:100]


def _device_label(user_agent: str) -> str:
    agent = user_agent.lower()
    browser = (
        "Edge"
        if "edg/" in agent
        else "Firefox"
        if "firefox/" in agent
        else "Chrome"
        if "chrome/" in agent
        else "Safari"
        if "safari/" in agent
        else "Browser"
    )
    platform = (
        "Windows"
        if "windows" in agent
        else "macOS"
        if "macintosh" in agent
        else "Android"
        if "android" in agent
        else "iOS"
        if re.search(r"iphone|ipad", agent)
        else "Linux"
        if "linux" in agent
        else "device"
    )
    return f"{browser} on {platform}"


@transaction.atomic
def create_account_session(*, user, request) -> AccountSession:
    if request.session.session_key is None:
        request.session.save()
    user_agent = str(request.META.get("HTTP_USER_AGENT", ""))[:255]
    ip = _request_ip(request)
    session = AccountSession.objects.create(
        user=user,
        django_session_key_hash=_keyed_hash(request.session.session_key),
        device_label=_device_label(user_agent),
        user_agent=user_agent,
        initial_ip_hash=_keyed_hash(ip) if ip else "",
        last_ip_hash=_keyed_hash(ip) if ip else "",
        expires_at=AccountSession.default_expiry(),
    )
    request.session["account_session_id"] = str(session.id)
    request.session.save()
    return session


def current_session_id(request) -> str | None:
    session_id = request.session.get("account_session_id") if hasattr(request, "session") else None
    if session_id:
        return str(session_id)
    auth = getattr(request, "auth", None)
    if auth is not None:
        sid = auth.get("sid")
        return str(sid) if sid else None
    return None


def get_active_session(*, user, session_id: str) -> AccountSession:
    session = AccountSession.objects.get(pk=session_id, user=user)
    if not session.is_active_session():
        if session.status == AccountSession.Status.ACTIVE:
            AccountSession.objects.filter(pk=session.pk).update(
                status=AccountSession.Status.EXPIRED
            )
        raise AccountSession.DoesNotExist
    return session


def touch_session(session: AccountSession, request=None) -> None:
    now = timezone.now()
    interval = timedelta(seconds=settings.ACCOUNT_SESSION_ACTIVITY_UPDATE_SECONDS)
    if session.last_seen_at > now - interval:
        return
    updates = {"last_seen_at": now}
    if request is not None:
        ip = _request_ip(request)
        if ip:
            updates["last_ip_hash"] = _keyed_hash(ip)
    AccountSession.objects.filter(
        pk=session.pk,
        status=AccountSession.Status.ACTIVE,
    ).update(**updates)


def _blacklist_session_tokens(session: AccountSession) -> None:
    for outstanding in OutstandingToken.objects.filter(user=session.user).iterator():
        try:
            token = RefreshToken(outstanding.token)
        except Exception:
            continue
        if str(token.get("sid", "")) == str(session.id):
            BlacklistedToken.objects.get_or_create(token=outstanding)


@transaction.atomic
def revoke_session(*, session: AccountSession, actor=None, reason: str = "") -> bool:
    locked = AccountSession.objects.select_for_update().get(pk=session.pk)
    if locked.status != AccountSession.Status.ACTIVE:
        return False
    locked.status = AccountSession.Status.REVOKED
    locked.revoked_at = timezone.now()
    locked.revoked_by = actor if getattr(actor, "is_authenticated", False) else None
    locked.revoke_reason = str(reason or "")[:255]
    locked.save(update_fields=["status", "revoked_at", "revoked_by", "revoke_reason"])
    _blacklist_session_tokens(locked)
    return True


@transaction.atomic
def revoke_user_sessions(
    *,
    user,
    actor=None,
    exclude_session_id: str | None = None,
    reason: str,
) -> int:
    sessions = list(
        AccountSession.objects.select_for_update().filter(
            user=user,
            status=AccountSession.Status.ACTIVE,
        )
    )
    count = 0
    for session in sessions:
        if exclude_session_id and str(session.id) == str(exclude_session_id):
            continue
        count += int(revoke_session(session=session, actor=actor, reason=reason))
    return count


def purge_django_session(session: AccountSession) -> None:
    if not session.django_session_key_hash:
        return
    for django_session in Session.objects.filter(expire_date__gt=timezone.now()).iterator():
        if _keyed_hash(django_session.session_key) == session.django_session_key_hash:
            django_session.delete()
            return
