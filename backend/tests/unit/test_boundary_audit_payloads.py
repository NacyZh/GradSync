from pathlib import Path

import pytest

from apps.audit.boundary_events import build_boundary_audit_payload, record_boundary_event
from tests.factories.shared_workspace import (
    active_student,
    project_with_members,
    standalone_shared_document,
)


@pytest.mark.django_db
def test_boundary_audit_payload_has_required_context_without_secrets_or_paths():
    actor = active_student()
    project = project_with_members(students=[actor])
    document = standalone_shared_document(project=project, source_project=project)

    payload = build_boundary_audit_payload(
        actor=actor,
        resource=document,
        boundary_type="standalone_shared",
        visibility_state="group_wide",
        source_project=project,
        action="download",
        outcome="success",
        metadata={
            "local_path": str(Path("/tmp/private/file.pdf")),
            "token": "secret-token",
            "request_id": "req-1",
        },
    )

    assert payload["actorId"] == actor.id
    assert payload["resourceType"] == "document"
    assert payload["resourceId"] == document.id
    assert payload["boundaryType"] == "standalone_shared"
    assert payload["visibilityState"] == "group_wide"
    assert payload["sourceProjectId"] == project.id
    assert payload["action"] == "download"
    assert payload["outcome"] == "success"
    assert payload["metadata"] == {"request_id": "req-1"}
    assert payload["occurredAt"]


@pytest.mark.django_db
def test_boundary_audit_event_accepts_system_actor_for_migration():
    project = project_with_members()
    event = record_boundary_event(
        actor=None,
        resource=None,
        boundary_type="project_material",
        visibility_state="project-only",
        source_project=project,
        action="migration_classify",
        outcome="pending_review",
        metadata={"record_count": 3},
    )

    assert event.actor is None
    assert event.project == project
    assert event.event_type == "boundary.migration_classify.pending_review"
    assert "project_material" in event.summary
