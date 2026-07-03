import pytest

from apps.resources.models import ResourceItem, ResourceType
from tests.factories.accounts import UserFactory
from tests.helpers import authenticate


@pytest.mark.django_db
def test_resource_inventory_crud_and_student_blocking_contract(api_client):
    teacher = UserFactory(global_role="advisor", status="active")
    student = UserFactory(global_role="student", status="active")

    empty_response = authenticate(api_client, student).get("/api/resources/")
    create_response = authenticate(api_client, teacher).post(
        "/api/resources/",
        {
            "name": "Confocal microscope",
            "resourceType": "Microscope",
            "description": "Shared imaging instrument",
            "useInstructions": "Submit a use request before access.",
        },
        format="json",
    )
    student_create_response = authenticate(api_client, student).post(
        "/api/resources/",
        {"name": "Student-created resource", "resourceType": "Bench"},
        format="json",
    )
    update_response = authenticate(api_client, teacher).patch(
        f"/api/resources/{create_response.data['id']}/",
        {"status": "unavailable", "useInstructions": "Temporarily offline."},
        format="json",
    )
    delete_response = authenticate(api_client, teacher).delete(
        f"/api/resources/{create_response.data['id']}/"
    )

    assert empty_response.status_code == 200
    assert empty_response.json()["results"] == []
    assert create_response.status_code == 201
    assert create_response.data["resourceType"] == "Microscope"
    assert create_response.data["status"] == "active"
    assert student_create_response.status_code == 403
    assert update_response.status_code == 200
    assert update_response.data["status"] == "unavailable"
    assert delete_response.status_code == 204


@pytest.mark.django_db
def test_resource_use_submission_create_and_decision_contract(api_client):
    teacher = UserFactory(global_role="advisor", status="active")
    student = UserFactory(global_role="student", status="active")
    resource_type = ResourceType.objects.create(name="Instrument")
    resource = ResourceItem.objects.create(
        resource_type=resource_type,
        name="Spectrometer",
        manager=teacher,
        use_instructions="Record usage after each session.",
    )

    submission_response = authenticate(api_client, student).post(
        f"/api/resources/{resource.id}/use-submissions/",
        {"submissionType": "request", "details": "Need two hours for sample scan."},
        format="json",
    )
    student_decision_response = authenticate(api_client, student).patch(
        f"/api/resource-use-submissions/{submission_response.data['id']}/",
        {"status": "confirmed"},
        format="json",
    )
    decision_response = authenticate(api_client, teacher).patch(
        f"/api/resource-use-submissions/{submission_response.data['id']}/",
        {"status": "confirmed", "decisionNote": "Approved for Friday."},
        format="json",
    )

    assert submission_response.status_code == 201
    assert submission_response.data["resourceId"] == resource.id
    assert submission_response.data["studentId"] == student.id
    assert submission_response.data["status"] == "pending"
    assert student_decision_response.status_code == 403
    assert decision_response.status_code == 200
    assert decision_response.data["status"] == "confirmed"
    assert decision_response.data["decisionNote"] == "Approved for Friday."
