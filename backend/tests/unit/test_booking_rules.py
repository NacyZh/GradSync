import pytest
from django.core.exceptions import ValidationError

from apps.projects.models import ProjectMembership, ResearchProject
from apps.resources.models import Booking, LabResource
from apps.resources.services import BookingService
from tests.factories.accounts import UserFactory


@pytest.mark.django_db
def test_booking_end_must_be_after_start():
    student = UserFactory(global_role="student")
    advisor = UserFactory(global_role="advisor")
    project = ResearchProject.objects.create(title="Project", advisor=advisor)
    ProjectMembership.objects.create(project=project, user=student, role="student")
    resource = LabResource.objects.create(name="Seat", resource_type="seat")

    with pytest.raises(ValidationError):
        BookingService(student, project).create_booking(
            resource=resource,
            starts_at="2026-06-26T11:00:00Z",
            ends_at="2026-06-26T10:00:00Z",
        )


@pytest.mark.django_db
def test_started_booking_cannot_be_changed_or_cancelled():
    student = UserFactory(global_role="student")
    advisor = UserFactory(global_role="advisor")
    project = ResearchProject.objects.create(title="Project", advisor=advisor)
    ProjectMembership.objects.create(project=project, user=student, role="student")
    resource = LabResource.objects.create(name="Seat", resource_type="seat")
    booking = Booking.objects.create(
        project=project,
        resource=resource,
        requested_by=student,
        starts_at="2026-06-25T10:00:00Z",
        ends_at="2026-06-25T11:00:00Z",
    )
    service = BookingService(student, project)

    with pytest.raises(ValidationError, match="before the reservation starts"):
        service.update_booking(booking, purpose="Too late")

    with pytest.raises(ValidationError, match="before the reservation starts"):
        service.cancel_booking(booking)
