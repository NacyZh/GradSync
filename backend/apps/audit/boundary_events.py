from __future__ import annotations

import json

from django.utils import timezone

from apps.audit.services import record_event

SECRET_METADATA_KEYS = {"token", "secret", "password", "local_path", "path", "stored_name"}


def _resource_type(resource) -> str:
    if resource is None:
        return ""
    name = resource.__class__.__name__
    return {
        "PaperRecord": "paper",
        "DocumentRecord": "document",
        "CodeArtifact": "code",
        "WritingProject": "writing",
        "ProjectMaterial": "project_material",
    }.get(name, name)


def _safe_metadata(metadata: dict | None) -> dict:
    safe = {}
    for key, value in (metadata or {}).items():
        normalized = str(key).lower()
        if normalized in SECRET_METADATA_KEYS or normalized.endswith("_path"):
            continue
        safe[str(key)] = value
    return safe


def build_boundary_audit_payload(
    *,
    actor,
    resource,
    boundary_type: str,
    visibility_state: str,
    source_project=None,
    action: str,
    outcome: str,
    metadata: dict | None = None,
) -> dict:
    return {
        "actorId": getattr(actor, "id", None) if actor is not None else None,
        "resourceType": _resource_type(resource),
        "resourceId": getattr(resource, "id", None) if resource is not None else None,
        "boundaryType": boundary_type,
        "visibilityState": visibility_state,
        "sourceProjectId": getattr(source_project, "id", None),
        "action": action,
        "outcome": outcome,
        "occurredAt": timezone.now().isoformat(),
        "metadata": _safe_metadata(metadata),
    }


def record_boundary_event(
    *,
    actor,
    resource,
    boundary_type: str,
    visibility_state: str,
    source_project=None,
    action: str,
    outcome: str,
    metadata: dict | None = None,
):
    payload = build_boundary_audit_payload(
        actor=actor,
        resource=resource,
        boundary_type=boundary_type,
        visibility_state=visibility_state,
        source_project=source_project,
        action=action,
        outcome=outcome,
        metadata=metadata,
    )
    return record_event(
        source_project,
        actor,
        f"boundary.{action}.{outcome}",
        json.dumps(payload, ensure_ascii=True, sort_keys=True),
        resource,
    )
