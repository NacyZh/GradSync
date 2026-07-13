import pytest
from django.core.exceptions import ValidationError
from django.utils import timezone

from apps.audit.models import AuditEvent
from apps.projects.models import ResearchProject
from apps.resources.models import Booking, ResourceItem, ResourceType, ResourceUseSubmission
from apps.resources.services import (
    BookingService,
    ResourceConflict,
    ResourceInventoryService,
    current_use_periods_by_resource,
    reconcile_completed_bookings,
)
from tests.factories.accounts import UserFactory


@pytest.mark.django_db
def test_quantity_policy_and_optimistic_version_rules():
    manager = UserFactory(global_role="advisor", status="active")
    resource_type = ResourceType.objects.create(
        name="Instrument", confirmation_policy=ResourceType.ConfirmationPolicy.APPROVAL_REQUIRED
    )
    resource = ResourceItem.objects.create(
        resource_type=resource_type, name="Microscope", total_quantity=3, manager=manager
    )
    assert resource.effective_confirmation_policy == "approval_required"
    resource.confirmation_policy_override = ResourceType.ConfirmationPolicy.IMMEDIATE
    assert resource.effective_confirmation_policy == "immediate"

    service = ResourceInventoryService(manager)
    with pytest.raises(ValidationError):
        service.update_resource(resource, version=99, total_quantity=2)
    updated = service.update_resource(resource, version=1, total_quantity=2)
    assert updated.total_quantity == 2
    assert updated.version == 2


@pytest.mark.django_db
def test_safe_minimum_and_delete_eligibility_preserve_audit_snapshot():
    manager = UserFactory(global_role="advisor", status="active")
    student = UserFactory(global_role="student", status="active")
    project = ResearchProject.objects.create(title="Legacy", advisor=manager)
    resource_type = ResourceType.objects.create(name="Seat")
    dependent = ResourceItem.objects.create(
        resource_type=resource_type, name="Dependent", total_quantity=2, manager=manager
    )
    starts = timezone.now() + timezone.timedelta(days=1)
    Booking.objects.create(
        project=project,
        resource_item=dependent,
        requested_by=student,
        starts_at=starts,
        ends_at=starts + timezone.timedelta(hours=1),
    )
    Booking.objects.create(
        project=project,
        resource_item=dependent,
        requested_by=student,
        starts_at=starts + timezone.timedelta(minutes=15),
        ends_at=starts + timezone.timedelta(minutes=45),
    )
    with pytest.raises(ValidationError):
        ResourceInventoryService(manager).update_resource(
            dependent, version=1, total_quantity=1
        )
    with pytest.raises(ValidationError):
        ResourceInventoryService(manager).delete_resource(dependent)

    deletable = ResourceItem.objects.create(
        resource_type=resource_type, name="Deletable", total_quantity=1, manager=manager
    )
    resource_id = deletable.pk
    ResourceInventoryService(manager).delete_resource(deletable)
    assert not ResourceItem.objects.filter(pk=resource_id).exists()
    event = AuditEvent.objects.get(event_type="resource.deleted", target_id=str(resource_id))
    assert event.target_snapshot["name"] == "Deletable"
    assert event.target_snapshot["outcome"] == "deleted"


@pytest.mark.django_db
def test_use_submission_dependency_requires_retirement():
    manager = UserFactory(global_role="admin", status="active")
    student = UserFactory(global_role="student", status="active")
    resource = ResourceItem.objects.create(
        resource_type=ResourceType.objects.create(name="Room"), name="Clean room", manager=manager
    )
    ResourceUseSubmission.objects.create(
        resource_item=resource,
        student=student,
        submission_type=ResourceUseSubmission.SubmissionType.REQUEST,
        details="Access",
    )
    with pytest.raises(ValidationError):
        ResourceInventoryService(manager).delete_resource(resource)
    retired = ResourceInventoryService(manager).retire_resource(resource)
    assert retired.status == ResourceItem.Status.RETIRED


@pytest.mark.django_db
def test_student_booking_is_pending_originated_and_capacity_validated():
    student = UserFactory(global_role="student", status="active")
    resource = ResourceItem.objects.create(
        resource_type=ResourceType.objects.create(
            name="Microscope",
            confirmation_policy=ResourceType.ConfirmationPolicy.APPROVAL_REQUIRED,
        ),
        name="Scope",
        total_quantity=2,
    )
    starts = timezone.now() + timezone.timedelta(days=1)

    booking = BookingService(student).create_booking(
        resource_item=resource,
        starts_at=starts,
        ends_at=starts + timezone.timedelta(hours=1),
        quantity=2,
        purpose="Imaging",
    )

    assert booking.status == Booking.Status.PENDING
    assert booking.origin == Booking.Origin.STUDENT_REQUEST
    assert booking.quantity == 2
    event = AuditEvent.objects.get(event_type="booking.created", target_id=str(booking.id))
    assert event.target_snapshot["origin"] == Booking.Origin.STUDENT_REQUEST
    assert event.target_snapshot["quantity"] == 2


@pytest.mark.django_db
def test_student_booking_rejects_unusable_or_over_capacity_resource():
    student = UserFactory(global_role="student", status="active")
    resource = ResourceItem.objects.create(
        resource_type=ResourceType.objects.create(
            name="Microscope",
            confirmation_policy=ResourceType.ConfirmationPolicy.APPROVAL_REQUIRED,
        ),
        name="Scope",
        total_quantity=1,
    )
    starts = timezone.now() + timezone.timedelta(days=1)

    with pytest.raises(ResourceConflict) as over_capacity:
        BookingService(student).create_booking(
            resource_item=resource,
            starts_at=starts,
            ends_at=starts + timezone.timedelta(hours=1),
            quantity=2,
        )
    assert over_capacity.value.payload["code"] == "insufficient_capacity"

    resource.status = ResourceItem.Status.RETIRED
    resource.save(update_fields=["status"])
    with pytest.raises(ValidationError):
        BookingService(student).create_booking(
            resource_item=resource,
            starts_at=starts,
            ends_at=starts + timezone.timedelta(hours=1),
            quantity=1,
        )


@pytest.mark.django_db
def test_student_can_cancel_own_not_started_booking_only():
    student = UserFactory(global_role="student", status="active")
    other_student = UserFactory(global_role="student", status="active")
    resource = ResourceItem.objects.create(
        resource_type=ResourceType.objects.create(
            name="Microscope",
            confirmation_policy=ResourceType.ConfirmationPolicy.APPROVAL_REQUIRED,
        ),
        name="Scope",
        total_quantity=1,
    )
    starts = timezone.now() + timezone.timedelta(days=1)
    booking = BookingService(student).create_booking(
        resource_item=resource,
        starts_at=starts,
        ends_at=starts + timezone.timedelta(hours=1),
        quantity=1,
    )

    with pytest.raises(ValidationError):
        BookingService(other_student).cancel_booking(booking)

    cancelled = BookingService(student).cancel_booking(booking)

    assert cancelled.status == Booking.Status.CANCELLED
    assert cancelled.cancelled_at is not None
    event = AuditEvent.objects.get(event_type="booking.cancelled", target_id=str(booking.id))
    assert event.target_snapshot["outcome"] == "cancelled"

    with pytest.raises(ResourceConflict):
        BookingService(student).cancel_booking(cancelled)


@pytest.mark.django_db
def test_manager_can_approve_reject_and_duplicate_decision_conflicts():
    manager = UserFactory(global_role="advisor", status="active")
    student = UserFactory(global_role="student", status="active")
    resource_type = ResourceType.objects.create(
        name="Microscope",
        confirmation_policy=ResourceType.ConfirmationPolicy.APPROVAL_REQUIRED,
    )
    resource = ResourceItem.objects.create(
        resource_type=resource_type,
        name="Scope",
        total_quantity=1,
    )
    starts = timezone.now() + timezone.timedelta(days=1)
    booking = BookingService(student).create_booking(
        resource_item=resource,
        starts_at=starts,
        ends_at=starts + timezone.timedelta(hours=1),
        quantity=1,
    )

    approved = BookingService(manager).decide_booking(booking, approve=True)

    assert approved.status == Booking.Status.CONFIRMED
    assert approved.reviewer == manager
    event = AuditEvent.objects.get(event_type="booking.confirmed", target_id=str(booking.id))
    assert event.target_snapshot["priorStatus"] == Booking.Status.PENDING
    assert event.target_snapshot["currentStatus"] == Booking.Status.CONFIRMED

    with pytest.raises(ResourceConflict) as duplicate:
        BookingService(manager).decide_booking(approved, approve=True)
    assert duplicate.value.payload["code"] == "duplicate_decision"
    assert AuditEvent.objects.filter(event_type="booking.duplicate_decision").exists()


@pytest.mark.django_db
def test_staff_direct_use_is_confirmed_for_current_or_future_own_use():
    manager = UserFactory(global_role="admin", status="active")
    resource = ResourceItem.objects.create(
        resource_type=ResourceType.objects.create(name="Microscope"),
        name="Scope",
        total_quantity=1,
    )
    now = timezone.now()

    booking = BookingService(manager).create_booking(
        resource_item=resource,
        starts_at=now - timezone.timedelta(minutes=1),
        ends_at=now + timezone.timedelta(hours=1),
        quantity=1,
        purpose="Calibration",
    )

    assert booking.status == Booking.Status.CONFIRMED
    assert booking.origin == Booking.Origin.STAFF_DIRECT
    assert booking.requested_by == manager

    with pytest.raises(ValidationError):
        BookingService(manager).create_booking(
            resource_item=resource,
            starts_at=now - timezone.timedelta(hours=2),
            ends_at=now - timezone.timedelta(hours=1),
            quantity=1,
        )


@pytest.mark.django_db
def test_completion_reconciliation_and_current_use_periods():
    manager = UserFactory(global_role="advisor", status="active")
    resource = ResourceItem.objects.create(
        resource_type=ResourceType.objects.create(name="Microscope"),
        name="Scope",
        total_quantity=2,
    )
    now = timezone.now()
    ended = Booking.objects.create(
        resource_item=resource,
        requested_by=manager,
        starts_at=now - timezone.timedelta(hours=3),
        ends_at=now - timezone.timedelta(hours=1),
        quantity=1,
        origin=Booking.Origin.STAFF_DIRECT,
        status=Booking.Status.CONFIRMED,
    )
    active = Booking.objects.create(
        resource_item=resource,
        requested_by=manager,
        starts_at=now - timezone.timedelta(minutes=10),
        ends_at=now + timezone.timedelta(hours=1),
        quantity=2,
        origin=Booking.Origin.STAFF_DIRECT,
        status=Booking.Status.CONFIRMED,
    )

    assert reconcile_completed_bookings(now) == 1
    ended.refresh_from_db()
    assert ended.status == Booking.Status.COMPLETED
    assert ended.completed_at is not None

    periods = current_use_periods_by_resource([resource.id], now=now)
    assert periods[resource.id] == [{
        "bookingId": active.id,
        "startsAt": active.starts_at.isoformat(),
        "endsAt": active.ends_at.isoformat(),
        "quantity": 2,
    }]
