import pytest

from apps.audit.models import AuditEvent
from apps.resources.models import ResourceItem, ResourceType, ResourceUseSubmission
from tests.factories.accounts import UserFactory
from tests.helpers import authenticate


@pytest.mark.django_db
def test_inventory_starts_empty_and_teacher_admin_manage_resources(api_client):
    teacher = UserFactory(global_role="advisor", status="active")
    admin = UserFactory(global_role="admin", status="active")
    student = UserFactory(global_role="student", status="active")

    assert ResourceItem.objects.count() == 0
    assert authenticate(api_client, student).get("/api/resources/").json()["results"] == []

    student_create = authenticate(api_client, student).post(
        "/api/resources/",
        {"name": "Student bench", "resourceType": "Bench", "totalQuantity": 1},
        format="json",
    )
    created = authenticate(api_client, teacher).post(
        "/api/resources/",
        {
            "name": "PCR workstation",
            "resourceType": "Instrument",
            "totalQuantity": 2,
            "description": "Amplifier",
        },
        format="json",
    )
    updated = authenticate(api_client, admin).patch(
        f"/api/resources/{created.data['id']}/",
        {"version": 1, "status": "unavailable", "description": "Service window"},
        format="json",
    )
    deleted = authenticate(api_client, teacher).delete(f"/api/resources/{created.data['id']}/")

    assert student_create.status_code == 403
    assert created.status_code == 201
    assert updated.status_code == 200
    assert deleted.status_code == 204
    assert not ResourceItem.objects.filter(pk=created.data["id"]).exists()
    assert AuditEvent.objects.filter(event_type="resource.created", actor=teacher).exists()
    assert AuditEvent.objects.filter(event_type="resource.updated", actor=admin).exists()
    assert AuditEvent.objects.filter(event_type="resource.deleted", actor=teacher).exists()


@pytest.mark.django_db
def test_student_use_submission_states_and_audit(api_client):
    teacher = UserFactory(global_role="advisor", status="active")
    student = UserFactory(global_role="student", status="active")
    resource_type = ResourceType.objects.create(name="Microscope")
    resource = ResourceItem.objects.create(
        resource_type=resource_type,
        name="Confocal microscope",
        manager=teacher,
    )

    created = authenticate(api_client, student).post(
        f"/api/resources/{resource.id}/use-submissions/",
        {"submissionType": "use_record", "details": "Used for calibration run."},
        format="json",
    )
    blocked_decision = authenticate(api_client, student).patch(
        f"/api/resource-use-submissions/{created.data['id']}/",
        {"status": "rejected", "decisionNote": "self-review"},
        format="json",
    )
    confirmed = authenticate(api_client, teacher).patch(
        f"/api/resource-use-submissions/{created.data['id']}/",
        {"status": "confirmed", "decisionNote": "Usage record accepted."},
        format="json",
    )
    repeat_decision = authenticate(api_client, teacher).patch(
        f"/api/resource-use-submissions/{created.data['id']}/",
        {"status": "rejected"},
        format="json",
    )

    assert created.status_code == 201
    assert blocked_decision.status_code == 403
    assert confirmed.status_code == 200
    assert confirmed.data["status"] == ResourceUseSubmission.Status.CONFIRMED
    assert repeat_decision.status_code == 400
    assert AuditEvent.objects.filter(event_type="resource.use_submitted", actor=student).exists()
    assert AuditEvent.objects.filter(event_type="resource.use_confirmed", actor=teacher).exists()


@pytest.mark.django_db
def test_retired_resources_cannot_receive_new_use_submissions(api_client):
    teacher = UserFactory(global_role="advisor", status="active")
    student = UserFactory(global_role="student", status="active")
    resource_type = ResourceType.objects.create(name="Room")
    resource = ResourceItem.objects.create(
        resource_type=resource_type,
        name="Clean room",
        manager=teacher,
        status=ResourceItem.Status.RETIRED,
    )

    response = authenticate(api_client, student).post(
        f"/api/resources/{resource.id}/use-submissions/",
        {"submissionType": "request", "details": "Access request"},
        format="json",
    )

    assert response.status_code == 400
    assert "retired" in str(response.json()).lower()
