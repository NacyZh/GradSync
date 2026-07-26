import pytest

from apps.audit.services import record_execution_event
from tests.factories.research_execution import execution_project


@pytest.mark.django_db
def test_execution_audit_keeps_attribution_and_drops_sensitive_payloads():
    project, actor = execution_project()
    event = record_execution_event(
        project=project,
        actor=actor,
        action="notification.acknowledged",
        target=project,
        state={
            "status": "acknowledged",
            "version": 2,
            "body": "private report body",
            "rationale": "private rationale",
            "url": "https://secret.invalid",
            "email": "hidden@example.com",
            "filename": "hidden.pdf",
            "token": "secret",
        },
        privileged=True,
    )

    assert event.actor_id == actor.id
    assert event.target_id == str(project.id)
    assert event.target_snapshot == {"status": "acknowledged", "version": 2}
