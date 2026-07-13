import pytest
from django.core.exceptions import ValidationError
from django.utils import timezone
from django.utils.dateparse import parse_datetime

from apps.projects.models import ProjectMembership, ResearchProject
from apps.resources.models import Booking, ResourceItem, ResourceType
from apps.resources.services import BookingService
from tests.factories.accounts import UserFactory


@pytest.mark.django_db
def test_overlapping_booking_is_rejected():
    student = UserFactory(global_role="student")
    advisor = UserFactory(global_role="advisor")
    project = ResearchProject.objects.create(title="Project", advisor=advisor)
    ProjectMembership.objects.create(project=project, user=student, role="student")
    resource_type = ResourceType.objects.create(name="seat", field_schema=[])
    resource = ResourceItem.objects.create(resource_type=resource_type, name="Seat")
    Booking.objects.create(
        project=project,
        resource_item=resource,
        requested_by=student,
        starts_at=parse_datetime("2026-06-26T10:00:00Z"),
        ends_at=parse_datetime("2026-06-26T11:00:00Z"),
    )

    with pytest.raises(ValidationError):
        BookingService(student, project).create_booking(
            resource_item=resource,
            starts_at=parse_datetime("2026-06-26T10:30:00Z"),
            ends_at=parse_datetime("2026-06-26T11:30:00Z"),
        )


@pytest.mark.django_db
def test_student_cancel_releases_future_capacity_for_requested_window():
    student = UserFactory(global_role="student", status="active")
    resource = ResourceItem.objects.create(
        resource_type=ResourceType.objects.create(name="seat", field_schema=[]),
        name="Seat",
        total_quantity=1,
    )
    starts = timezone.now() + timezone.timedelta(days=1)
    booking = BookingService(student).create_booking(
        resource_item=resource,
        starts_at=starts,
        ends_at=starts + timezone.timedelta(hours=1),
        quantity=1,
    )

    cancelled = BookingService(student).cancel_booking(booking)
    assert cancelled.status == Booking.Status.CANCELLED

    replacement = BookingService(student).create_booking(
        resource_item=resource,
        starts_at=starts,
        ends_at=starts + timezone.timedelta(hours=1),
        quantity=1,
    )
    assert replacement.status == Booking.Status.PENDING


@pytest.mark.django_db
def test_concurrent_approval_and_direct_use_do_not_exceed_capacity():
    manager = UserFactory(global_role="advisor", status="active")
    student = UserFactory(global_role="student", status="active")
    resource = ResourceItem.objects.create(
        resource_type=ResourceType.objects.create(name="seat", field_schema=[]),
        name="Seat",
        total_quantity=1,
    )
    starts = timezone.now() + timezone.timedelta(days=1)
    pending = BookingService(student).create_booking(
        resource_item=resource,
        starts_at=starts,
        ends_at=starts + timezone.timedelta(hours=1),
        quantity=1,
    )
    direct = BookingService(manager).create_booking(
        resource_item=resource,
        starts_at=starts,
        ends_at=starts + timezone.timedelta(hours=1),
        quantity=1,
    )
    assert direct.status == Booking.Status.CONFIRMED

    with pytest.raises(ValidationError):
        BookingService(manager).decide_booking(pending, approve=True)
