import pytest
from django.utils import timezone

from apps.projects.models import ProjectMembership, ResearchProject
from apps.resources.models import Booking, ResourceItem, ResourceType
from tests.factories.accounts import UserFactory
from tests.helpers import authenticate


@pytest.mark.django_db
def test_resource_list_and_booking_create(api_client):
    student = UserFactory(global_role="student")
    advisor = UserFactory(global_role="advisor")
    project = ResearchProject.objects.create(title="Project", advisor=advisor)
    ProjectMembership.objects.create(project=project, user=student, role="student")
    resource_type = ResourceType.objects.create(
        name="Lab seat",
        field_schema=[
            {
                "key": "capacity",
                "label": "Capacity",
                "fieldType": "number",
                "required": False,
            }
        ],
    )
    resource = ResourceItem.objects.create(
        resource_type=resource_type,
        name="Seat 1",
        location="Lab",
        field_values={"capacity": 1},
    )

    resources_response = authenticate(api_client, student).get("/api/resource-items/")
    assert resources_response.status_code == 200

    starts_at = timezone.now() + timezone.timedelta(days=2)
    ends_at = starts_at + timezone.timedelta(hours=1)

    booking_response = api_client.post(
        f"/api/projects/{project.id}/bookings/",
        {
            "resourceItemId": resource.id,
            "starts_at": starts_at.isoformat(),
            "ends_at": ends_at.isoformat(),
        },
        format="json",
    )
    assert booking_response.status_code == 201


@pytest.mark.django_db
def test_student_booking_api_creates_pending_request_and_allows_cancel(api_client):
    student = UserFactory(global_role="student", status="active")
    resource = ResourceItem.objects.create(
        resource_type=ResourceType.objects.create(
            name="Microscope",
            confirmation_policy=ResourceType.ConfirmationPolicy.APPROVAL_REQUIRED,
        ),
        name="Scope",
        total_quantity=4,
    )
    starts_at = timezone.now() + timezone.timedelta(days=2)
    ends_at = starts_at + timezone.timedelta(hours=2)

    client = authenticate(api_client, student)
    create_response = client.post(
        "/api/bookings/",
        {
            "resourceId": resource.id,
            "startsAt": starts_at.isoformat(),
            "endsAt": ends_at.isoformat(),
            "quantity": 2,
            "purpose": "Imaging",
        },
        format="json",
    )

    assert create_response.status_code == 201
    assert create_response.data["status"] == Booking.Status.PENDING
    assert create_response.data["origin"] == Booking.Origin.STUDENT_REQUEST
    assert create_response.data["quantity"] == 2
    assert create_response.data["completedAt"] is None
    assert create_response.data["resourceName"] == "Scope"

    list_response = client.get("/api/bookings/")
    assert list_response.status_code == 200
    assert list_response.data["results"][0]["id"] == create_response.data["id"]

    cancel_response = client.post(f"/api/bookings/{create_response.data['id']}/cancel/")
    assert cancel_response.status_code == 200
    assert cancel_response.data["status"] == Booking.Status.CANCELLED
    assert cancel_response.data["cancelledAt"] is not None


@pytest.mark.django_db
def test_student_booking_api_rejects_other_student_cancel(api_client):
    student = UserFactory(global_role="student", status="active")
    other_student = UserFactory(global_role="student", status="active")
    resource = ResourceItem.objects.create(
        resource_type=ResourceType.objects.create(name="Microscope"),
        name="Scope",
        total_quantity=1,
    )
    starts_at = timezone.now() + timezone.timedelta(days=2)
    booking = Booking.objects.create(
        resource_item=resource,
        requested_by=student,
        starts_at=starts_at,
        ends_at=starts_at + timezone.timedelta(hours=1),
        quantity=1,
        origin=Booking.Origin.STUDENT_REQUEST,
        status=Booking.Status.PENDING,
    )

    cancel_response = authenticate(api_client, other_student).post(
        f"/api/bookings/{booking.id}/cancel/"
    )

    assert cancel_response.status_code == 404


@pytest.mark.django_db
def test_manager_review_queue_and_decision_endpoints(api_client):
    manager = UserFactory(global_role="advisor", status="active")
    student = UserFactory(global_role="student", status="active")
    resource = ResourceItem.objects.create(
        resource_type=ResourceType.objects.create(name="Microscope"),
        name="Scope",
        total_quantity=2,
    )
    starts_at = timezone.now() + timezone.timedelta(days=2)
    booking = Booking.objects.create(
        resource_item=resource,
        requested_by=student,
        starts_at=starts_at,
        ends_at=starts_at + timezone.timedelta(hours=1),
        quantity=1,
        origin=Booking.Origin.STUDENT_REQUEST,
        status=Booking.Status.PENDING,
    )

    client = authenticate(api_client, manager)
    queue_response = client.get("/api/bookings/?reviewQueue=true")
    assert queue_response.status_code == 200
    assert queue_response.data["results"][0]["id"] == booking.id
    assert queue_response.data["results"][0]["requesterName"] == student.name

    approve_response = client.post(f"/api/bookings/{booking.id}/approve/", {"decisionNote": "OK"})
    assert approve_response.status_code == 200
    assert approve_response.data["status"] == Booking.Status.CONFIRMED

    duplicate_response = client.post(f"/api/bookings/{booking.id}/approve/")
    assert duplicate_response.status_code == 409
    assert duplicate_response.data["code"] == "duplicate_decision"


@pytest.mark.django_db
def test_student_cannot_access_review_queue_or_decide(api_client):
    student = UserFactory(global_role="student", status="active")
    other_student = UserFactory(global_role="student", status="active")
    resource = ResourceItem.objects.create(
        resource_type=ResourceType.objects.create(name="Microscope"),
        name="Scope",
        total_quantity=1,
    )
    starts_at = timezone.now() + timezone.timedelta(days=2)
    booking = Booking.objects.create(
        resource_item=resource,
        requested_by=other_student,
        starts_at=starts_at,
        ends_at=starts_at + timezone.timedelta(hours=1),
        quantity=1,
        origin=Booking.Origin.STUDENT_REQUEST,
        status=Booking.Status.PENDING,
    )

    client = authenticate(api_client, student)
    queue_response = client.get("/api/bookings/?reviewQueue=true")
    assert queue_response.status_code == 200
    assert queue_response.data["results"] == []

    approve_response = client.post(f"/api/bookings/{booking.id}/approve/")
    assert approve_response.status_code == 404


@pytest.mark.django_db
def test_staff_direct_booking_api_is_confirmed_and_not_in_review_queue(api_client):
    manager = UserFactory(global_role="admin", status="active")
    resource = ResourceItem.objects.create(
        resource_type=ResourceType.objects.create(name="Microscope"),
        name="Scope",
        total_quantity=2,
    )
    starts_at = timezone.now()
    response = authenticate(api_client, manager).post(
        "/api/bookings/",
        {
            "resourceId": resource.id,
            "startsAt": starts_at.isoformat(),
            "endsAt": (starts_at + timezone.timedelta(hours=1)).isoformat(),
            "quantity": 1,
            "purpose": "Calibration",
        },
        format="json",
    )
    assert response.status_code == 201
    assert response.data["status"] == Booking.Status.CONFIRMED
    assert response.data["origin"] == Booking.Origin.STAFF_DIRECT

    queue_response = api_client.get("/api/bookings/?reviewQueue=true")
    assert queue_response.status_code == 200
    assert queue_response.data["results"] == []


@pytest.mark.django_db
def test_resource_availability_returns_freshness_and_current_use_periods(api_client):
    manager = UserFactory(global_role="advisor", status="active")
    resource = ResourceItem.objects.create(
        resource_type=ResourceType.objects.create(name="Microscope"),
        name="Scope",
        total_quantity=3,
    )
    now = timezone.now()
    active = Booking.objects.create(
        resource_item=resource,
        requested_by=manager,
        starts_at=now - timezone.timedelta(minutes=5),
        ends_at=now + timezone.timedelta(hours=1),
        quantity=2,
        origin=Booking.Origin.STAFF_DIRECT,
        status=Booking.Status.CONFIRMED,
    )

    response = authenticate(api_client, manager).get(
        "/api/resources/availability/",
        {
            "startsAt": (now - timezone.timedelta(minutes=1)).isoformat(),
            "endsAt": (now + timezone.timedelta(hours=2)).isoformat(),
        },
    )

    assert response.status_code == 200
    assert response.data["observedAt"]
    assert response.data["freshnessToken"]
    item = response.data["results"][0]
    assert item["id"] == resource.id
    assert item["availableQuantity"] == 1
    assert item["currentUsePeriods"][0]["bookingId"] == active.id
    assert item["currentUsePeriods"][0]["quantity"] == 2
