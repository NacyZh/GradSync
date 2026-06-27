import pytest

from apps.projects.models import ProjectMembership, ResearchProject
from apps.resources.models import Booking, LabResource
from tests.factories.accounts import UserFactory
from tests.helpers import authenticate


@pytest.mark.django_db
def test_booking_list_is_project_scoped(api_client):
    student = UserFactory(global_role="student")
    other = UserFactory(global_role="student")
    advisor = UserFactory(global_role="advisor")
    project = ResearchProject.objects.create(title="A", advisor=advisor)
    hidden = ResearchProject.objects.create(title="B", advisor=advisor)
    resource = LabResource.objects.create(name="Seat", resource_type="seat")
    ProjectMembership.objects.create(project=project, user=student, role="student")
    ProjectMembership.objects.create(project=hidden, user=other, role="student")
    Booking.objects.create(
        project=project,
        resource=resource,
        requested_by=student,
        starts_at="2026-06-26T10:00:00Z",
        ends_at="2026-06-26T11:00:00Z",
    )
    Booking.objects.create(
        project=hidden,
        resource=resource,
        requested_by=other,
        starts_at="2026-06-26T12:00:00Z",
        ends_at="2026-06-26T13:00:00Z",
    )

    response = authenticate(api_client, student).get(f"/api/projects/{project.id}/bookings/")

    assert response.status_code == 200
    assert len(response.json()["results"]) == 1
