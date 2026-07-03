import pytest
from django.utils import timezone

from apps.projects.models import ProjectMembership, ResearchProject
from apps.resources.models import Booking, ResourceItem, ResourceType
from tests.factories.accounts import UserFactory
from tests.helpers import authenticate


@pytest.mark.django_db
def test_booking_list_is_project_scoped(api_client):
    student = UserFactory(global_role="student")
    other = UserFactory(global_role="student")
    advisor = UserFactory(global_role="advisor")
    project = ResearchProject.objects.create(title="A", advisor=advisor)
    hidden = ResearchProject.objects.create(title="B", advisor=advisor)
    resource_type = ResourceType.objects.create(name="seat", field_schema=[])
    resource = ResourceItem.objects.create(resource_type=resource_type, name="Seat")
    ProjectMembership.objects.create(project=project, user=student, role="student")
    ProjectMembership.objects.create(project=hidden, user=other, role="student")
    Booking.objects.create(
        project=project,
        resource_item=resource,
        requested_by=student,
        starts_at="2026-06-26T10:00:00Z",
        ends_at="2026-06-26T11:00:00Z",
    )
    Booking.objects.create(
        project=hidden,
        resource_item=resource,
        requested_by=other,
        starts_at="2026-06-26T12:00:00Z",
        ends_at="2026-06-26T13:00:00Z",
    )

    response = authenticate(api_client, student).get(f"/api/projects/{project.id}/bookings/")

    assert response.status_code == 200
    assert len(response.json()["results"]) == 1


@pytest.mark.django_db
def test_started_booking_cancel_returns_validation_error(api_client):
    student = UserFactory(global_role="student")
    advisor = UserFactory(global_role="advisor")
    project = ResearchProject.objects.create(title="Project", advisor=advisor)
    ProjectMembership.objects.create(project=project, user=student, role="student")
    resource_type = ResourceType.objects.create(name="seat", field_schema=[])
    resource = ResourceItem.objects.create(resource_type=resource_type, name="Seat")
    booking = Booking.objects.create(
        project=project,
        resource_item=resource,
        requested_by=student,
        starts_at=timezone.now() - timezone.timedelta(minutes=5),
        ends_at=timezone.now() + timezone.timedelta(minutes=55),
    )

    response = authenticate(api_client, student).post(
        f"/api/projects/{project.id}/bookings/{booking.id}/cancel/"
    )

    assert response.status_code == 400
    assert "before the reservation starts" in str(response.json())
