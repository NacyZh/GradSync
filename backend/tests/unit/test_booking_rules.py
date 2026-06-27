import pytest
from django.core.exceptions import ValidationError

from apps.projects.models import ProjectMembership, ResearchProject
from apps.resources.models import LabResource
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
