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
