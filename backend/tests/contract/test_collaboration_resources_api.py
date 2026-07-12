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
            "totalQuantity": 3,
            "description": "Shared imaging instrument",
            "useInstructions": "Submit a use request before access.",
        },
        format="json",
    )
    student_create_response = authenticate(api_client, student).post(
        "/api/resources/",
        {"name": "Student-created resource", "resourceType": "Bench", "totalQuantity": 1},
        format="json",
    )
    update_response = authenticate(api_client, teacher).patch(
        f"/api/resources/{create_response.data['id']}/",
        {"version": 1, "status": "unavailable", "useInstructions": "Temporarily offline."},
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
    assert create_response.data["totalQuantity"] == 3
    assert student_create_response.status_code == 403
    assert update_response.status_code == 200
    assert update_response.data["status"] == "unavailable"
    assert delete_response.status_code == 204


@pytest.mark.django_db
def test_resource_item_compatibility_endpoint_is_read_only_and_does_not_leak_history(api_client):
    student = UserFactory(global_role="student", status="active")
    resource_type = ResourceType.objects.create(name="Instrument")
    resource = ResourceItem.objects.create(resource_type=resource_type, name="Spectrometer")

    blocked = authenticate(api_client, student).post(
        "/api/resource-items/",
        {"resourceTypeId": resource_type.id, "name": "Unauthorized"},
        format="json",
    )
    listed = authenticate(api_client, student).get("/api/resources/")

    assert blocked.status_code == 405
    assert listed.status_code == 200
    item = next(row for row in listed.data["results"] if row["id"] == resource.id)
    assert "useSubmissions" not in item


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
