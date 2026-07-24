from collections.abc import Callable, Mapping
from typing import Any

from django.db import transaction

from apps.common.middleware import request_id_var

from .models import AuditEvent

REDACTION_VERSION = 1
_DENIED_KEYS = {
    "authorization",
    "body",
    "bytes",
    "code",
    "content",
    "cookie",
    "csrf",
    "file",
    "password",
    "raw",
    "secret",
    "session",
    "token",
}


def _is_denied_key(key: str) -> bool:
    normalized = key.lower().replace("-", "_")
    return any(part in normalized for part in _DENIED_KEYS)


def _redact_value(value: Any) -> Any:
    if isinstance(value, Mapping):
        return {
            str(key)[:100]: _redact_value(item)
            for key, item in value.items()
            if not _is_denied_key(str(key))
        }
    if isinstance(value, (list, tuple)):
        return [_redact_value(item) for item in value[:100]]
    if isinstance(value, str):
        return value[:1000]
    if value is None or isinstance(value, (bool, int, float)):
        return value
    return str(value)[:1000]


def redact_snapshot(
    snapshot: Mapping[str, Any] | None,
    *,
    allowed_keys: set[str] | None = None,
) -> dict[str, Any]:
    source = snapshot or {}
    return {
        str(key)[:100]: _redact_value(value)
        for key, value in source.items()
        if not _is_denied_key(str(key)) and (allowed_keys is None or str(key) in allowed_keys)
    }


def _actor_snapshot(actor) -> dict[str, Any]:
    if not getattr(actor, "is_authenticated", False):
        return {}
    return {
        "id": actor.pk,
        "email": str(getattr(actor, "email", ""))[:254],
        "name": str(getattr(actor, "name", ""))[:255],
        "role": str(getattr(actor, "global_role", ""))[:30],
    }


def record_event(
    project,
    actor,
    event_type: str,
    summary: str,
    target=None,
    *,
    target_snapshot=None,
    allowed_snapshot_keys: set[str] | None = None,
    category: str = AuditEvent.Category.OTHER,
    outcome: str = AuditEvent.Outcome.SUCCEEDED,
    reason: str = "",
    correlation_id: str | None = None,
) -> AuditEvent:
    target_type = target.__class__.__name__ if target is not None else ""
    target_id = str(getattr(target, "pk", "")) if target is not None else ""
    return AuditEvent.objects.create(
        project=project,
        actor=actor if getattr(actor, "is_authenticated", False) else None,
        event_type=event_type,
        target_type=target_type,
        target_id=target_id,
        target_snapshot=redact_snapshot(target_snapshot, allowed_keys=allowed_snapshot_keys),
        category=category,
        outcome=outcome,
        reason=str(reason or "")[:1000],
        correlation_id=(correlation_id or request_id_var.get("-"))[:64],
        actor_snapshot=_actor_snapshot(actor),
        redaction_version=REDACTION_VERSION,
        summary=summary,
    )


@transaction.atomic
def audited_mutation(
    mutation: Callable[[], Any],
    *,
    project,
    actor,
    event_type: str,
    summary: str,
    target=None,
    target_snapshot=None,
    allowed_snapshot_keys: set[str] | None = None,
    category: str = AuditEvent.Category.OTHER,
    outcome: str = AuditEvent.Outcome.SUCCEEDED,
    reason: str = "",
):
    result = mutation()
    effective_target = target(result) if callable(target) else target
    effective_snapshot = target_snapshot(result) if callable(target_snapshot) else target_snapshot
    record_event(
        project,
        actor,
        event_type,
        summary,
        effective_target,
        target_snapshot=effective_snapshot,
        allowed_snapshot_keys=allowed_snapshot_keys,
        category=category,
        outcome=outcome,
        reason=reason,
    )
    return result


def record_role_activation(actor, target, action: str, reason: str = "") -> AuditEvent:
    return record_event(
        None,
        actor,
        f"role_activation.{action}",
        f"Role activation {action}",
        target,
        target_snapshot={
            "requestedRole": target.requested_role,
            "status": target.status,
            "reason": reason,
        },
    )


def record_upload(project, actor, target, asset_type: str) -> AuditEvent:
    return record_event(project, actor, f"{asset_type}.uploaded", f"Uploaded {asset_type}", target)


def record_download(project, actor, target, asset_type: str) -> AuditEvent:
    return record_event(
        project, actor, f"{asset_type}.downloaded", f"Downloaded {asset_type}", target
    )


def record_membership_change(project, actor, target, action: str) -> AuditEvent:
    return record_event(project, actor, f"membership.{action}", f"Membership {action}", target)


def record_feedback_event(project, actor, target, action: str) -> AuditEvent:
    return record_event(project, actor, f"feedback.{action}", f"Feedback {action}", target)


def record_resource_decision(project, actor, target, action: str) -> AuditEvent:
    return record_event(project, actor, f"resource.{action}", f"Resource {action}", target)


def record_notification_status(project, actor, target, status: str) -> AuditEvent:
    return record_event(project, actor, f"notification.{status}", f"Notification {status}", target)


def record_schedule_event(*, actor, schedule_item, action: str, outcome: str, audience=None):
    """Record group schedule operations without copying schedule content."""
    if schedule_item.scope == "personal":
        return None
    snapshot = {
        "scope": schedule_item.scope,
        "outcome": outcome,
        "audience": audience or {},
        "version": schedule_item.version,
    }
    return record_event(
        None,
        actor,
        f"schedule.{action}",
        f"Group schedule {action}: {outcome}",
        schedule_item,
        target_snapshot=snapshot,
    )
