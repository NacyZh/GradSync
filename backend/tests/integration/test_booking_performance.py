import pytest
from django.utils import timezone

from apps.projects.models import ProjectMembership, ResearchProject
from apps.resources.models import Booking, ResourceItem, ResourceType
from tests.factories.accounts import UserFactory
from tests.helpers import authenticate


@pytest.mark.django_db
def test_booking_list_handles_project_scoped_records(api_client):
    advisor = UserFactory(global_role="advisor")
    student = UserFactory(global_role="student")
    project = ResearchProject.objects.create(title="Performance", advisor=advisor)
    ProjectMembership.objects.create(project=project, user=student, role="student")
    resource_type = ResourceType.objects.create(name="seat", field_schema=[])
    resource = ResourceItem.objects.create(resource_type=resource_type, name="Seat")
    Booking.objects.bulk_create(
        [
            Booking(
                project=project,
                resource_item=resource,
                requested_by=student,
                starts_at=f"2026-06-26T{index % 24:02d}:00:00Z",
                ends_at=f"2026-06-26T{index % 24:02d}:30:00Z",
            )
            for index in range(100)
        ]
    )

    response = authenticate(api_client, student).get(f"/api/projects/{project.id}/bookings/")

    assert response.status_code == 200
    assert len(response.json()["results"]) == 50


@pytest.mark.django_db
def test_resource_availability_handles_1000_resources_with_bounded_queries(
    api_client, django_assert_max_num_queries
):
    advisor = UserFactory(global_role="advisor", status="active")
    resource_type = ResourceType.objects.create(name="seat", field_schema=[])
    resources = ResourceItem.objects.bulk_create(
        [
            ResourceItem(resource_type=resource_type, name=f"Seat {index}", total_quantity=3)
            for index in range(1000)
        ]
    )
    now = timezone.now()
    Booking.objects.bulk_create(
        [
            Booking(
                resource_item=resource,
                requested_by=advisor,
                starts_at=now - timezone.timedelta(minutes=5),
                ends_at=now + timezone.timedelta(hours=1),
                quantity=1,
                origin=Booking.Origin.STAFF_DIRECT,
                status=Booking.Status.CONFIRMED,
            )
            for resource in resources[:100]
        ]
    )

    client = authenticate(api_client, advisor)
    with django_assert_max_num_queries(8):
        response = client.get(
            "/api/resources/availability/",
            {
                "startsAt": now.isoformat(),
                "endsAt": (now + timezone.timedelta(hours=2)).isoformat(),
            },
        )

    assert response.status_code == 200
    assert len(response.json()["results"]) == 1000
    assert response.json()["results"][0]["availableQuantity"] == 2
