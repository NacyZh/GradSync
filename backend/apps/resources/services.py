from django.core.exceptions import ValidationError
from django.db import transaction
from django.utils import timezone
from django.utils.dateparse import parse_datetime

from apps.audit.services import record_event
from apps.common.project_scope import ProjectScopedService
from apps.notifications.models import Notification
from apps.notifications.services import enqueue_notification
from apps.projects.archive_services import ensure_project_writable

from .models import Booking, ResourceItem, ResourceType, ResourceUseSubmission


def _is_resource_manager(user) -> bool:
    return (
        getattr(user, "is_authenticated", False)
        and getattr(user, "status", "") == "active"
        and getattr(user, "global_role", "") in {"advisor", "admin"}
    )


def _is_active_student(user) -> bool:
    return (
        getattr(user, "is_authenticated", False)
        and getattr(user, "status", "") == "active"
        and getattr(user, "global_role", "") == "student"
    )


def resource_status_to_contract(status: str) -> str:
    if status == ResourceItem.Status.AVAILABLE:
        return "active"
    return status


def resource_status_from_contract(status: str) -> str:
    if status == "active":
        return ResourceItem.Status.AVAILABLE
    if status in {ResourceItem.Status.UNAVAILABLE, ResourceItem.Status.RETIRED}:
        return status
    raise ValidationError("Unsupported resource status")


class ResourceInventoryService:
    def __init__(self, user):
        self.user = user

    def require_manager(self) -> None:
        if not _is_resource_manager(self.user):
            raise PermissionError("Only teachers and administrators can manage resources")

    def require_student(self) -> None:
        if not _is_active_student(self.user):
            raise PermissionError("Only active students can submit resource use")

    @transaction.atomic
    def create_resource(
        self,
        *,
        name: str,
        resource_type: str,
        description: str = "",
        use_instructions: str = "",
    ) -> ResourceItem:
        self.require_manager()
        if not name.strip() or not resource_type.strip():
            raise ValidationError("Resource name and type are required")
        resource_type_obj, _ = ResourceType.objects.get_or_create(
            name=resource_type.strip(),
            defaults={"field_schema": []},
        )
        resource = ResourceItem.objects.create(
            resource_type=resource_type_obj,
            name=name.strip(),
            description=description.strip(),
            use_instructions=use_instructions.strip(),
            manager=self.user,
        )
        record_event(
            None, self.user, "resource.created", f"Created resource {resource.id}", resource
        )
        return resource

    @transaction.atomic
    def update_resource(self, resource: ResourceItem, **attrs) -> ResourceItem:
        self.require_manager()
        if "name" in attrs and attrs["name"] is not None:
            if not attrs["name"].strip():
                raise ValidationError("Resource name is required")
            resource.name = attrs["name"].strip()
        if "resource_type" in attrs and attrs["resource_type"] is not None:
            if not attrs["resource_type"].strip():
                raise ValidationError("Resource type is required")
            resource.resource_type, _ = ResourceType.objects.get_or_create(
                name=attrs["resource_type"].strip(),
                defaults={"field_schema": []},
            )
        if "description" in attrs and attrs["description"] is not None:
            resource.description = attrs["description"].strip()
        if "use_instructions" in attrs and attrs["use_instructions"] is not None:
            resource.use_instructions = attrs["use_instructions"].strip()
        if "status" in attrs and attrs["status"] is not None:
            resource.status = resource_status_from_contract(attrs["status"])
        resource.manager = resource.manager or self.user
        resource.full_clean()
        resource.save()
        record_event(
            None, self.user, "resource.updated", f"Updated resource {resource.id}", resource
        )
        return resource

    @transaction.atomic
    def retire_resource(self, resource: ResourceItem) -> ResourceItem:
        self.require_manager()
        resource.status = ResourceItem.Status.RETIRED
        resource.save(update_fields=["status", "updated_at"])
        record_event(
            None, self.user, "resource.retired", f"Retired resource {resource.id}", resource
        )
        return resource

    @transaction.atomic
    def create_use_submission(
        self,
        resource: ResourceItem,
        *,
        submission_type: str,
        details: str,
    ) -> ResourceUseSubmission:
        self.require_student()
        if resource.status == ResourceItem.Status.RETIRED:
            raise ValidationError("Retired resources cannot receive new use submissions")
        if submission_type not in ResourceUseSubmission.SubmissionType.values:
            raise ValidationError("Unsupported resource use submission type")
        if not details.strip():
            raise ValidationError("Use submission details are required")
        submission = ResourceUseSubmission.objects.create(
            resource_item=resource,
            student=self.user,
            submission_type=submission_type,
            details=details.strip(),
        )
        record_event(
            None,
            self.user,
            "resource.use_submitted",
            f"Submitted resource use {submission.id}",
            submission,
        )
        return submission

    @transaction.atomic
    def decide_use_submission(
        self,
        submission: ResourceUseSubmission,
        *,
        status: str,
        decision_note: str = "",
    ) -> ResourceUseSubmission:
        self.require_manager()
        if submission.status != ResourceUseSubmission.Status.PENDING:
            raise ValidationError("Only pending resource use submissions can be decided")
        if status not in {
            ResourceUseSubmission.Status.CONFIRMED,
            ResourceUseSubmission.Status.REJECTED,
        }:
            raise ValidationError("Resource use decision must be confirmed or rejected")
        submission.status = status
        submission.reviewer = self.user
        submission.decision_note = decision_note.strip()
        submission.decided_at = timezone.now()
        submission.save(
            update_fields=["status", "reviewer", "decision_note", "decided_at"]
        )
        action = (
            "use_confirmed"
            if status == ResourceUseSubmission.Status.CONFIRMED
            else "use_rejected"
        )
        record_event(None, self.user, f"resource.{action}", f"Resource {action}", submission)
        enqueue_notification(
            recipient=submission.student,
            sender=self.user,
            event_type=Notification.EventType.RESOURCE_USE_DECISION,
            target_type="ResourceUseSubmission",
            target_id=str(submission.id),
            subject=f"Resource use {status}",
            action_path="/resources",
        )
        return submission


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
