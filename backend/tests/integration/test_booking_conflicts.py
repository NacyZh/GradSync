import pytest
from django.core.exceptions import ValidationError
from django.utils.dateparse import parse_datetime

from apps.projects.models import ProjectMembership, ResearchProject
from apps.resources.models import Booking, LabResource
from apps.resources.services import BookingService
from tests.factories.accounts import UserFactory


@pytest.mark.django_db
def test_overlapping_booking_is_rejected():
    student = UserFactory(global_role="student")
    advisor = UserFactory(global_role="advisor")
    project = ResearchProject.objects.create(title="Project", advisor=advisor)
    ProjectMembership.objects.create(project=project, user=student, role="student")
    resource = LabResource.objects.create(name="Seat", resource_type="seat")
    Booking.objects.create(
        project=project,
        resource=resource,
        requested_by=student,
        starts_at=parse_datetime("2026-06-26T10:00:00Z"),
        ends_at=parse_datetime("2026-06-26T11:00:00Z"),
    )

    with pytest.raises(ValidationError):
        BookingService(student, project).create_booking(
            resource=resource,
            starts_at=parse_datetime("2026-06-26T10:30:00Z"),
            ends_at=parse_datetime("2026-06-26T11:30:00Z"),
        )
