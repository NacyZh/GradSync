from .models import AuditEvent


def record_event(project, actor, event_type: str, summary: str, target=None) -> AuditEvent:
    target_type = target.__class__.__name__ if target is not None else ""
    target_id = str(getattr(target, "pk", "")) if target is not None else ""
    return AuditEvent.objects.create(
        project=project,
        actor=actor if getattr(actor, "is_authenticated", False) else None,
        event_type=event_type,
        target_type=target_type,
        target_id=target_id,
        summary=summary,
    )


def record_role_activation(actor, target, action: str) -> AuditEvent:
    return record_event(None, actor, f"role_activation.{action}", f"Role activation {action}", target)


def record_upload(project, actor, target, asset_type: str) -> AuditEvent:
    return record_event(project, actor, f"{asset_type}.uploaded", f"Uploaded {asset_type}", target)


def record_download(project, actor, target, asset_type: str) -> AuditEvent:
    return record_event(project, actor, f"{asset_type}.downloaded", f"Downloaded {asset_type}", target)


def record_membership_change(project, actor, target, action: str) -> AuditEvent:
    return record_event(project, actor, f"membership.{action}", f"Membership {action}", target)


def record_feedback_event(project, actor, target, action: str) -> AuditEvent:
    return record_event(project, actor, f"feedback.{action}", f"Feedback {action}", target)


def record_resource_decision(project, actor, target, action: str) -> AuditEvent:
    return record_event(project, actor, f"resource.{action}", f"Resource {action}", target)


def record_notification_status(project, actor, target, status: str) -> AuditEvent:
    return record_event(project, actor, f"notification.{status}", f"Notification {status}", target)
