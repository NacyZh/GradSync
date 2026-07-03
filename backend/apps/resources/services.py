from django.core.exceptions import ValidationError
from django.db import transaction
from django.utils import timezone
from django.utils.dateparse import parse_datetime

from apps.audit.services import record_event
from apps.common.project_scope import ProjectScopedService
from apps.notifications.models import Notification
from apps.projects.archive_services import ensure_project_writable

from .models import Booking


class BookingService(ProjectScopedService):
    def __init__(self, user, project):
        super().__init__(user)
        self.project = project

    def _ensure_future_booking(self, booking: Booking) -> None:
        starts_at = (
            parse_datetime(booking.starts_at)
            if isinstance(booking.starts_at, str)
            else booking.starts_at
        )
        if starts_at <= timezone.now():
            raise ValidationError("Bookings can only be changed before the reservation starts")

    @transaction.atomic
    def create_booking(self, *, resource_item, starts_at, ends_at, purpose: str = "") -> Booking:
        self.require_project_member(self.project)
        ensure_project_writable(self.project)
        starts_at = parse_datetime(starts_at) if isinstance(starts_at, str) else starts_at
        ends_at = parse_datetime(ends_at) if isinstance(ends_at, str) else ends_at
        if not starts_at or not ends_at or ends_at <= starts_at:
            raise ValidationError("Booking end time must be after start time")
        conflict = Booking.objects.select_for_update().filter(
            resource_item=resource_item,
            status=Booking.Status.RESERVED,
            starts_at__lt=ends_at,
            ends_at__gt=starts_at,
        )
        if conflict.exists():
            raise ValidationError("Resource is unavailable for the selected time")
        booking = Booking.objects.create(
            project=self.project,
            resource_item=resource_item,
            requested_by=self.user,
            starts_at=starts_at,
            ends_at=ends_at,
            purpose=purpose,
        )
        self._notify_booking_change(booking, "Booking confirmed")
        record_event(
            self.project, self.user, "booking.created", f"Created booking {booking.id}", booking
        )
        return booking

    @transaction.atomic
    def update_booking(
        self, booking: Booking, *, starts_at=None, ends_at=None, purpose: str | None = None
    ) -> Booking:
        self.require_project_member(self.project)
        ensure_project_writable(self.project)
        self._ensure_future_booking(booking)
        if (
            booking.requested_by_id != self.user.id
            and not self.project.memberships.filter(
                user=self.user, status="active", role="advisor"
            ).exists()
        ):
            raise ValidationError("Only the requester or an advisor can change this booking")
        starts_at = (
            parse_datetime(starts_at)
            if isinstance(starts_at, str)
            else (starts_at or booking.starts_at)
        )
        ends_at = (
            parse_datetime(ends_at) if isinstance(ends_at, str) else (ends_at or booking.ends_at)
        )
        if not starts_at or not ends_at or ends_at <= starts_at:
            raise ValidationError("Booking end time must be after start time")
        conflict = (
            Booking.objects.select_for_update()
            .filter(
                resource_item=booking.resource_item,
                status=Booking.Status.RESERVED,
                starts_at__lt=ends_at,
                ends_at__gt=starts_at,
            )
            .exclude(pk=booking.pk)
        )
        if conflict.exists():
            raise ValidationError("Resource is unavailable for the selected time")
        booking.starts_at = starts_at
        booking.ends_at = ends_at
        if purpose is not None:
            booking.purpose = purpose
        booking.save()
        self._notify_booking_change(booking, "Booking changed")
        record_event(
            self.project, self.user, "booking.changed", f"Changed booking {booking.id}", booking
        )
        return booking

    def cancel_booking(self, booking: Booking) -> Booking:
        self.require_project_member(self.project)
        ensure_project_writable(self.project)
        self._ensure_future_booking(booking)
        if (
            booking.requested_by_id != self.user.id
            and not self.project.memberships.filter(
                user=self.user, status="active", role="advisor"
            ).exists()
        ):
            raise ValidationError("Only the requester or an advisor can cancel this booking")
        booking.status = Booking.Status.CANCELLED
        booking.cancelled_at = timezone.now()
        booking.save(update_fields=["status", "cancelled_at", "updated_at"])
        self._notify_booking_change(booking, "Booking cancelled")
        record_event(
            self.project, self.user, "booking.cancelled", f"Cancelled booking {booking.id}", booking
        )
        return booking

    def _notify_booking_change(self, booking: Booking, subject: str) -> None:
        for membership in self.project.memberships.filter(status="active"):
            Notification.objects.create(
                project=self.project,
                recipient=membership.user,
                event_type=Notification.EventType.BOOKING_CHANGED,
                target_type="Booking",
                target_id=str(booking.id),
                subject=subject,
                action_path=f"/projects/{self.project.id}/bookings/{booking.id}",
                sender=self.user,
                eligible_at=timezone.now(),
            )
