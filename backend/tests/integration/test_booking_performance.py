import pytest

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
    resource = ResourceItem.objects.create(resource_type=ResourceType.objects.create(name="seat", field_schema=[]), name="Seat")
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
