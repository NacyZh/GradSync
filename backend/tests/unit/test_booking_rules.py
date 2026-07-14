import pytest
from django.core.exceptions import ValidationError
from django.utils import timezone

from apps.resources.models import Booking, ResourceItem, ResourceType
from apps.resources.services import BookingService, ResourceConflict
from tests.factories.accounts import UserFactory


@pytest.mark.django_db
def test_booking_end_must_be_after_start():
    student = UserFactory(global_role="student")
    resource_type = ResourceType.objects.create(name="seat", field_schema=[])
    resource = ResourceItem.objects.create(resource_type=resource_type, name="Seat")

    with pytest.raises(ValidationError):
        BookingService(student).create_booking(
            resource_item=resource,
            starts_at="2026-06-26T11:00:00Z",
            ends_at="2026-06-26T10:00:00Z",
        )


@pytest.mark.django_db
def test_started_booking_cannot_be_changed_or_cancelled():
    student = UserFactory(global_role="student")
    resource_type = ResourceType.objects.create(name="seat", field_schema=[])
    resource = ResourceItem.objects.create(resource_type=resource_type, name="Seat")
    booking = Booking.objects.create(
        resource_item=resource,
        requested_by=student,
        starts_at="2026-06-25T10:00:00Z",
        ends_at="2026-06-25T11:00:00Z",
    )
    service = BookingService(student)

    with pytest.raises(ValidationError, match="before the reservation starts"):
        service.update_booking(booking, purpose="Too late")

    with pytest.raises(ValidationError, match="before the reservation starts"):
        service.cancel_booking(booking)


@pytest.mark.django_db
def test_active_booking_can_be_returned_early():
    student = UserFactory(global_role="student")
    resource_type = ResourceType.objects.create(name="scope", field_schema=[])
    resource = ResourceItem.objects.create(resource_type=resource_type, name="Scope")
    now = timezone.now()
    booking = Booking.objects.create(
        resource_item=resource,
        requested_by=student,
        starts_at=now - timezone.timedelta(minutes=30),
        ends_at=now + timezone.timedelta(hours=2),
        status=Booking.Status.CONFIRMED,
    )

    returned = BookingService(student).return_booking(booking)

    assert returned.status == Booking.Status.COMPLETED
    assert returned.completed_at is not None
    assert returned.ends_at <= timezone.now()
    assert returned.version == booking.version + 1


@pytest.mark.django_db
def test_future_booking_cannot_be_returned():
    student = UserFactory(global_role="student")
    resource_type = ResourceType.objects.create(name="scope", field_schema=[])
    resource = ResourceItem.objects.create(resource_type=resource_type, name="Scope")
    starts_at = timezone.now() + timezone.timedelta(hours=1)
    booking = Booking.objects.create(
        resource_item=resource,
        requested_by=student,
        starts_at=starts_at,
        ends_at=starts_at + timezone.timedelta(hours=2),
        status=Booking.Status.CONFIRMED,
    )

    with pytest.raises(ResourceConflict) as conflict:
        BookingService(student).return_booking(booking)
    assert conflict.value.payload["code"] == "return_window_invalid"


@pytest.mark.django_db
def test_quantity_capacity_and_policy_snapshot():
    student = UserFactory(global_role="student")
    resource_type = ResourceType.objects.create(name="GPU", confirmation_policy="immediate")
    resource = ResourceItem.objects.create(
        resource_type=resource_type, name="GPU", total_quantity=3
    )
    starts = timezone.now() + timezone.timedelta(days=1)
    service = BookingService(student)
    first = service.create_booking(
        resource_item=resource,
        starts_at=starts,
        ends_at=starts + timezone.timedelta(hours=1),
        quantity=2,
    )
    assert first.status == Booking.Status.CONFIRMED
    assert first.confirmation_policy == "immediate"
    with pytest.raises(ResourceConflict) as conflict:
        service.create_booking(
            resource_item=resource,
            starts_at=starts,
            ends_at=starts + timezone.timedelta(hours=1),
            quantity=2,
        )
    assert conflict.value.payload["availableQuantity"] == 1


@pytest.mark.django_db
def test_pending_approval_rechecks_capacity():
    student = UserFactory(global_role="student")
    manager = UserFactory(global_role="advisor")
    resource_type = ResourceType.objects.create(
        name="Scope", confirmation_policy="approval_required"
    )
    resource = ResourceItem.objects.create(
        resource_type=resource_type, name="Scope", total_quantity=1
    )
    starts = timezone.now() + timezone.timedelta(days=1)
    pending = BookingService(student).create_booking(
        resource_item=resource, starts_at=starts, ends_at=starts + timezone.timedelta(hours=1)
    )
    assert pending.status == Booking.Status.PENDING
    resource.confirmation_policy_override = "immediate"
    resource.save(update_fields=["confirmation_policy_override"])
    BookingService(student).create_booking(
        resource_item=resource, starts_at=starts, ends_at=starts + timezone.timedelta(hours=1)
    )
    with pytest.raises(ResourceConflict):
        BookingService(manager).decide_booking(pending, approve=True)
