from datetime import timedelta
from decimal import Decimal

from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError
from django.db import models, transaction
from django.db.models import Q, Sum
from django.utils import timezone
from django.utils.dateparse import parse_datetime

from apps.audit.services import record_event
from apps.notifications.models import Notification
from apps.notifications.services import enqueue_notification

from .models import (
    Booking,
    ConsumableStockTransaction,
    ResourceItem,
    ResourceMaintenanceRecord,
    ResourceType,
    ResourceUseSubmission,
)


class ResourceConflict(ValidationError):
    def __init__(self, payload):
        self.payload = payload
        super().__init__(payload.get("detail") or payload.get("code") or "Resource conflict")


def record_booking_conflict(*, actor, resource, payload, project=None):
    record_event(
        project,
        actor,
        "booking.resource_conflict",
        f"Booking conflict for resource {resource.id}",
        resource,
        target_snapshot={
            "resourceId": resource.id,
            "outcome": "resource_conflict",
            **payload,
        },
    )


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


def _booking_snapshot(booking: Booking, *, outcome: str, prior_status: str | None = None):
    return {
        "bookingId": booking.pk,
        "requesterId": booking.requested_by_id,
        "resourceId": booking.resource_item_id,
        "quantity": booking.quantity,
        "startsAt": booking.starts_at.isoformat() if booking.starts_at else None,
        "endsAt": booking.ends_at.isoformat() if booking.ends_at else None,
        "origin": booking.origin,
        "priorStatus": prior_status,
        "currentStatus": booking.status,
        "outcome": outcome,
    }


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


def reconcile_completed_bookings(now=None) -> int:
    now = now or timezone.now()
    updated = Booking.objects.filter(
        status__in=[Booking.Status.CONFIRMED, Booking.Status.RESERVED],
        ends_at__lte=now,
        completed_at__isnull=True,
    ).update(status=Booking.Status.COMPLETED, completed_at=now)
    if updated:
        record_event(
            None,
            None,
            "booking.completion_reconciled",
            f"Completed {updated} ended booking(s)",
            target_snapshot={"completedCount": updated, "observedAt": now.isoformat()},
        )
    return updated


def current_use_periods_by_resource(resource_ids, now=None, *, limit_per_resource=3):
    now = now or timezone.now()
    grouped = {resource_id: [] for resource_id in resource_ids}
    if not grouped:
        return grouped
    bookings = (
        Booking.objects.filter(
            resource_item_id__in=grouped.keys(),
            status__in=[Booking.Status.CONFIRMED, Booking.Status.RESERVED],
            starts_at__lte=now,
            ends_at__gt=now,
        )
        .order_by("resource_item_id", "ends_at", "starts_at")
        .values("id", "resource_item_id", "starts_at", "ends_at", "quantity")
    )
    for booking in bookings:
        periods = grouped[booking["resource_item_id"]]
        if len(periods) >= limit_per_resource:
            continue
        periods.append(
            {
                "bookingId": booking["id"],
                "startsAt": booking["starts_at"].isoformat(),
                "endsAt": booking["ends_at"].isoformat(),
                "quantity": booking["quantity"],
            }
        )
    return grouped


def _resource_notification_recipients(resource):
    if resource.manager_id:
        return [resource.manager]
    return list(
        get_user_model().objects.filter(
            global_role="admin",
            status="active",
        )
    )


def reconcile_resource_operation_alerts(today=None) -> int:
    today = today or timezone.localdate()
    now = timezone.now()
    alerted = 0
    scheduled_outages = ResourceMaintenanceRecord.objects.filter(
        resource_item_id=models.OuterRef("pk"),
        takes_offline=True,
        status__in=[
            ResourceMaintenanceRecord.Status.SCHEDULED,
            ResourceMaintenanceRecord.Status.IN_PROGRESS,
        ],
    ).filter(
        Q(status=ResourceMaintenanceRecord.Status.IN_PROGRESS)
        | Q(kind=ResourceMaintenanceRecord.Kind.FAULT)
        | Q(scheduled_at__lte=now)
    )
    ResourceItem.objects.filter(
        kind=ResourceItem.Kind.EQUIPMENT,
        status=ResourceItem.Status.AVAILABLE,
    ).filter(models.Exists(scheduled_outages)).update(
        status=ResourceItem.Status.UNAVAILABLE,
        version=models.F("version") + 1,
    )
    resources = (
        ResourceItem.objects.select_related("manager")
        .filter(
            kind=ResourceItem.Kind.EQUIPMENT,
            next_calibration_at__lte=today,
        )
        .exclude(status=ResourceItem.Status.RETIRED)
    )
    for resource in resources:
        if resource.status == ResourceItem.Status.AVAILABLE:
            resource.status = ResourceItem.Status.UNAVAILABLE
            resource.version += 1
            resource.save(update_fields=["status", "version", "updated_at"])
        for recipient in _resource_notification_recipients(resource):
            dedupe_subject = (
                f"Calibration overdue: {resource.name} ({resource.next_calibration_at})"
            )
            if Notification.objects.filter(
                recipient=recipient,
                event_type=Notification.EventType.RESOURCE_MAINTENANCE_DUE,
                target_type="ResourceItem",
                target_id=str(resource.id),
                subject=dedupe_subject,
            ).exists():
                continue
            enqueue_notification(
                recipient=recipient,
                event_type=Notification.EventType.RESOURCE_MAINTENANCE_DUE,
                target_type="ResourceItem",
                target_id=str(resource.id),
                subject=dedupe_subject,
                action_path="/resources",
                category=Notification.Category.ADMINISTRATION,
            )
            alerted += 1
    return alerted


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
        total_quantity: int = 1,
        location: str = "",
        description: str = "",
        use_instructions: str = "",
        status: str = "active",
        confirmation_policy_override: str | None = None,
        kind: str = ResourceItem.Kind.EQUIPMENT,
        stock_on_hand: int = 0,
        reorder_level: int = 0,
        stock_unit: str = "",
        unit_cost: Decimal = Decimal("0"),
        calibration_interval_days: int | None = None,
        next_calibration_at=None,
    ) -> ResourceItem:
        self.require_manager()
        if not name.strip() or not resource_type.strip():
            raise ValidationError("Resource name and type are required")
        if total_quantity < 1:
            raise ValidationError({"totalQuantity": "Resource quantity must be at least 1"})
        resource_type_obj, _ = ResourceType.objects.get_or_create(
            name=resource_type.strip(),
            defaults={"field_schema": []},
        )
        resource = ResourceItem.objects.create(
            resource_type=resource_type_obj,
            name=name.strip(),
            total_quantity=total_quantity,
            location=location.strip(),
            description=description.strip(),
            use_instructions=use_instructions.strip(),
            status=resource_status_from_contract(status),
            confirmation_policy_override=confirmation_policy_override,
            manager=self.user,
            kind=kind,
            stock_on_hand=stock_on_hand,
            reorder_level=reorder_level,
            stock_unit=stock_unit.strip(),
            unit_cost=unit_cost,
            calibration_interval_days=calibration_interval_days,
            next_calibration_at=next_calibration_at,
        )
        resource.full_clean()
        if resource.kind == ResourceItem.Kind.CONSUMABLE and resource.stock_on_hand:
            ConsumableStockTransaction.objects.create(
                resource_item=resource,
                kind=ConsumableStockTransaction.Kind.ADJUSTMENT,
                quantity_delta=resource.stock_on_hand,
                balance_after=resource.stock_on_hand,
                unit_cost=resource.unit_cost,
                note="Opening balance",
                recorded_by=self.user,
            )
        if (
            resource.kind == ResourceItem.Kind.CONSUMABLE
            and resource.stock_on_hand <= resource.reorder_level
        ):
            for recipient in _resource_notification_recipients(resource):
                enqueue_notification(
                    recipient=recipient,
                    sender=self.user,
                    event_type=Notification.EventType.RESOURCE_LOW_STOCK,
                    target_type="ResourceItem",
                    target_id=str(resource.id),
                    subject=(
                        f"Low stock: {resource.name} "
                        f"({resource.stock_on_hand} {resource.stock_unit})"
                    ),
                    action_path="/resources",
                    category=Notification.Category.ADMINISTRATION,
                )
        record_event(
            None, self.user, "resource.created", f"Created resource {resource.id}", resource
        )
        return resource

    @transaction.atomic
    def update_resource(self, resource: ResourceItem, **attrs) -> ResourceItem:
        self.require_manager()
        resource = (
            ResourceItem.objects.select_for_update()
            .select_related("resource_type")
            .get(pk=resource.pk)
        )
        expected_version = attrs.pop("version", None)
        if expected_version is None or expected_version != resource.version:
            raise ResourceConflict(
                {
                    "code": "stale_resource_version",
                    "currentVersion": resource.version,
                }
            )
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
        if "location" in attrs and attrs["location"] is not None:
            resource.location = attrs["location"].strip()
        if "total_quantity" in attrs and attrs["total_quantity"] is not None:
            requested_quantity = attrs["total_quantity"]
            if requested_quantity < 1:
                raise ValidationError({"totalQuantity": "Resource quantity must be at least 1"})
            safe_minimum = self._safe_minimum_quantity(resource)
            if requested_quantity < safe_minimum:
                raise ResourceConflict(
                    {
                        "code": "quantity_commitment_conflict",
                        "safeMinimum": safe_minimum,
                    }
                )
            resource.total_quantity = requested_quantity
        if "use_instructions" in attrs and attrs["use_instructions"] is not None:
            resource.use_instructions = attrs["use_instructions"].strip()
        if "status" in attrs and attrs["status"] is not None:
            resource.status = resource_status_from_contract(attrs["status"])
        if "confirmation_policy_override" in attrs:
            override = attrs["confirmation_policy_override"]
            if override not in {None, *ResourceType.ConfirmationPolicy.values}:
                raise ValidationError({"confirmationPolicyOverride": "Unsupported policy"})
            resource.confirmation_policy_override = override
        requested_kind = attrs.get("kind")
        if requested_kind and requested_kind != resource.kind:
            has_history = (
                resource.bookings.exists()
                or resource.use_submissions.exists()
                or resource.maintenance_records.exists()
                or resource.stock_transactions.exists()
            )
            if has_history:
                raise ResourceConflict(
                    {
                        "code": "resource_kind_has_history",
                        "detail": "Resource class cannot change after operational history exists",
                    }
                )
        for field in (
            "kind",
            "reorder_level",
            "unit_cost",
        ):
            if field in attrs and attrs[field] is not None:
                setattr(resource, field, attrs[field])
        for field in ("calibration_interval_days", "next_calibration_at"):
            if field in attrs:
                setattr(resource, field, attrs[field])
        if "stock_unit" in attrs and attrs["stock_unit"] is not None:
            resource.stock_unit = attrs["stock_unit"].strip()
        resource.manager = resource.manager or self.user
        resource.version += 1
        resource.full_clean()
        resource.save()
        record_event(
            None, self.user, "resource.updated", f"Updated resource {resource.id}", resource
        )
        return resource

    @staticmethod
    def _safe_minimum_quantity(resource: ResourceItem) -> int:
        events = []
        bookings = resource.bookings.filter(
            status__in=[Booking.Status.CONFIRMED, Booking.Status.RESERVED]
        )
        for starts_at, ends_at in bookings.values_list("starts_at", "ends_at"):
            events.append((starts_at, 1))
            events.append((ends_at, -1))
        active = safe_minimum = 0
        for _, delta in sorted(events, key=lambda item: (item[0], item[1])):
            active += delta
            safe_minimum = max(safe_minimum, active)
        return max(1, safe_minimum)

    @transaction.atomic
    def retire_resource(self, resource: ResourceItem) -> ResourceItem:
        self.require_manager()
        resource = ResourceItem.objects.select_for_update().get(pk=resource.pk)
        resource.status = ResourceItem.Status.RETIRED
        resource.version += 1
        resource.save(update_fields=["status", "version", "updated_at"])
        record_event(
            None, self.user, "resource.retired", f"Retired resource {resource.id}", resource
        )
        return resource

    @transaction.atomic
    def delete_resource(self, resource: ResourceItem) -> None:
        self.require_manager()
        resource = (
            ResourceItem.objects.select_for_update()
            .select_related("resource_type")
            .get(pk=resource.pk)
        )
        dependency_counts = {
            "bookings": resource.bookings.count(),
            "useSubmissions": resource.use_submissions.count(),
            "maintenanceRecords": resource.maintenance_records.count(),
            "stockTransactions": resource.stock_transactions.count(),
        }
        snapshot = {
            "resourceId": resource.pk,
            "name": resource.name,
            "resourceType": resource.resource_type.name,
            "totalQuantity": resource.total_quantity,
        }
        if any(dependency_counts.values()):
            record_event(
                None,
                self.user,
                "resource.delete_rejected",
                f"Rejected deletion of resource {resource.pk}",
                resource,
                target_snapshot={**snapshot, "outcome": "rejected", **dependency_counts},
            )
            raise ResourceConflict(
                {
                    "code": "resource_has_history",
                    "canRetire": True,
                    "dependencyCounts": dependency_counts,
                }
            )
        resource_id = resource.pk
        record_event(
            None,
            self.user,
            "resource.deleted",
            f"Deleted resource {resource_id}",
            resource,
            target_snapshot={**snapshot, "outcome": "deleted"},
        )
        resource.delete()

    @transaction.atomic
    def create_use_submission(
        self,
        resource: ResourceItem,
        *,
        submission_type: str,
        details: str,
    ) -> ResourceUseSubmission:
        self.require_student()
        if resource.kind == ResourceItem.Kind.CONSUMABLE:
            raise ValidationError("Consumables must be issued from stock")
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
        submission.save(update_fields=["status", "reviewer", "decision_note", "decided_at"])
        action = (
            "use_confirmed" if status == ResourceUseSubmission.Status.CONFIRMED else "use_rejected"
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


class ResourceOperationsService:
    def __init__(self, user):
        self.user = user

    def _require_manager(self):
        if not _is_resource_manager(self.user):
            raise PermissionError("Only teachers and administrators can manage resource operations")

    @transaction.atomic
    def create_maintenance(
        self,
        *,
        resource,
        kind,
        title,
        scheduled_at,
        due_at=None,
        details="",
        provider="",
        takes_offline=True,
        cost=Decimal("0"),
    ):
        self._require_manager()
        resource = ResourceItem.objects.select_for_update().get(pk=resource.pk)
        if resource.kind != ResourceItem.Kind.EQUIPMENT:
            raise ValidationError("Maintenance records apply only to equipment")
        if not title.strip():
            raise ValidationError({"title": "Maintenance title is required"})
        if due_at and due_at < scheduled_at:
            raise ValidationError({"dueAt": "Maintenance due time cannot precede its start"})
        record = ResourceMaintenanceRecord.objects.create(
            resource_item=resource,
            kind=kind,
            title=title.strip(),
            scheduled_at=scheduled_at,
            due_at=due_at,
            details=details.strip(),
            provider=provider.strip(),
            takes_offline=takes_offline,
            cost=cost,
            created_by=self.user,
        )
        if takes_offline and (
            kind == ResourceMaintenanceRecord.Kind.FAULT or scheduled_at <= timezone.now()
        ):
            ResourceItem.objects.filter(
                pk=resource.pk,
            ).exclude(status=ResourceItem.Status.RETIRED).update(
                status=ResourceItem.Status.UNAVAILABLE,
                version=models.F("version") + 1,
            )
        record_event(
            None,
            self.user,
            "resource.maintenance_created",
            f"Created maintenance record {record.id}",
            record,
        )
        return record

    @transaction.atomic
    def transition_maintenance(self, record, *, status, details=None):
        self._require_manager()
        record = (
            ResourceMaintenanceRecord.objects.select_for_update()
            .select_related("resource_item")
            .get(pk=record.pk)
        )
        if record.status in {
            ResourceMaintenanceRecord.Status.COMPLETED,
            ResourceMaintenanceRecord.Status.CANCELLED,
        }:
            raise ValidationError("Closed maintenance records are immutable")
        if status not in {
            ResourceMaintenanceRecord.Status.IN_PROGRESS,
            ResourceMaintenanceRecord.Status.COMPLETED,
            ResourceMaintenanceRecord.Status.CANCELLED,
        }:
            raise ValidationError("Unsupported maintenance transition")
        record.status = status
        if details is not None:
            record.details = details.strip()
        if status == ResourceMaintenanceRecord.Status.COMPLETED:
            record.completed_at = timezone.now()
            record.completed_by = self.user
            resource = record.resource_item
            if (
                record.kind == ResourceMaintenanceRecord.Kind.CALIBRATION
                and resource.calibration_interval_days
            ):
                resource.next_calibration_at = timezone.localdate() + timedelta(
                    days=resource.calibration_interval_days
                )
            other_outages = (
                resource.maintenance_records.filter(
                    takes_offline=True,
                    status__in=[
                        ResourceMaintenanceRecord.Status.SCHEDULED,
                        ResourceMaintenanceRecord.Status.IN_PROGRESS,
                    ],
                )
                .exclude(pk=record.pk)
                .filter(
                    Q(status=ResourceMaintenanceRecord.Status.IN_PROGRESS)
                    | Q(kind=ResourceMaintenanceRecord.Kind.FAULT)
                    | Q(scheduled_at__lte=timezone.now())
                )
            )
            if not other_outages.exists() and resource.status != ResourceItem.Status.RETIRED:
                resource.status = ResourceItem.Status.AVAILABLE
            resource.version += 1
            resource.save()
        elif status == ResourceMaintenanceRecord.Status.IN_PROGRESS and record.takes_offline:
            ResourceItem.objects.filter(pk=record.resource_item_id).exclude(
                status=ResourceItem.Status.RETIRED
            ).update(
                status=ResourceItem.Status.UNAVAILABLE,
                version=models.F("version") + 1,
            )
        elif status == ResourceMaintenanceRecord.Status.CANCELLED and record.takes_offline:
            resource = ResourceItem.objects.select_for_update().get(pk=record.resource_item_id)
            other_outages = (
                resource.maintenance_records.filter(
                    takes_offline=True,
                    status__in=[
                        ResourceMaintenanceRecord.Status.SCHEDULED,
                        ResourceMaintenanceRecord.Status.IN_PROGRESS,
                    ],
                )
                .exclude(pk=record.pk)
                .filter(
                    Q(status=ResourceMaintenanceRecord.Status.IN_PROGRESS)
                    | Q(kind=ResourceMaintenanceRecord.Kind.FAULT)
                    | Q(scheduled_at__lte=timezone.now())
                )
            )
            if not other_outages.exists() and resource.status != ResourceItem.Status.RETIRED:
                resource.status = ResourceItem.Status.AVAILABLE
                resource.version += 1
                resource.save(update_fields=["status", "version", "updated_at"])
        record.save()
        record_event(
            None,
            self.user,
            f"resource.maintenance_{status}",
            f"Maintenance record {record.id} changed to {status}",
            record,
        )
        return record

    @transaction.atomic
    def record_stock_transaction(
        self,
        *,
        resource,
        kind,
        quantity_delta,
        project=None,
        unit_cost=None,
        note="",
    ):
        self._require_manager()
        if (
            project is not None
            and getattr(self.user, "global_role", "") != "admin"
            and not project.memberships.filter(user=self.user, status="active").exists()
        ):
            raise PermissionError("Stock costs can only be assigned to a managed project")
        resource = ResourceItem.objects.select_for_update().get(pk=resource.pk)
        if resource.kind != ResourceItem.Kind.CONSUMABLE:
            raise ValidationError("Stock transactions apply only to consumables")
        if quantity_delta == 0:
            raise ValidationError({"quantityDelta": "Quantity change cannot be zero"})
        if kind == ConsumableStockTransaction.Kind.RECEIPT and quantity_delta < 0:
            raise ValidationError("Receipts must increase stock")
        if kind == ConsumableStockTransaction.Kind.ISSUE and quantity_delta > 0:
            raise ValidationError("Issues must decrease stock")
        new_balance = resource.stock_on_hand + quantity_delta
        if new_balance < 0:
            raise ResourceConflict(
                {
                    "code": "insufficient_consumable_stock",
                    "availableQuantity": resource.stock_on_hand,
                    "requestedQuantity": abs(quantity_delta),
                }
            )
        prior_balance = resource.stock_on_hand
        resource.stock_on_hand = new_balance
        resource.version += 1
        resource.save(update_fields=["stock_on_hand", "version", "updated_at"])
        transaction_record = ConsumableStockTransaction.objects.create(
            resource_item=resource,
            project=project,
            kind=kind,
            quantity_delta=quantity_delta,
            balance_after=new_balance,
            unit_cost=resource.unit_cost if unit_cost is None else unit_cost,
            note=note.strip(),
            recorded_by=self.user,
        )
        record_event(
            project,
            self.user,
            "resource.stock_recorded",
            f"Recorded stock transaction {transaction_record.id}",
            transaction_record,
            target_snapshot={
                "resourceId": resource.id,
                "quantityDelta": quantity_delta,
                "balanceAfter": new_balance,
            },
        )
        if prior_balance > resource.reorder_level and new_balance <= resource.reorder_level:
            for recipient in _resource_notification_recipients(resource):
                enqueue_notification(
                    recipient=recipient,
                    sender=self.user,
                    event_type=Notification.EventType.RESOURCE_LOW_STOCK,
                    target_type="ResourceItem",
                    target_id=str(resource.id),
                    subject=f"Low stock: {resource.name} ({new_balance} {resource.stock_unit})",
                    action_path="/resources",
                    category=Notification.Category.ADMINISTRATION,
                )
        return transaction_record


class BookingService:
    def __init__(self, user, project=None):
        self.user = user
        self.project = project

    def _require_active_user(self):
        if (
            not getattr(self.user, "is_authenticated", False)
            or getattr(self.user, "status", "") != "active"
        ):
            raise PermissionError("An active account is required")

    def _require_manager(self):
        if not _is_resource_manager(self.user):
            raise PermissionError("Only teachers and administrators can decide bookings")

    def _ensure_future_booking(self, booking: Booking) -> None:
        starts_at = (
            parse_datetime(booking.starts_at)
            if isinstance(booking.starts_at, str)
            else booking.starts_at
        )
        if starts_at <= timezone.now():
            raise ValidationError("Bookings can only be changed before the reservation starts")

    def _window(self, starts_at, ends_at):
        starts_at = parse_datetime(starts_at) if isinstance(starts_at, str) else starts_at
        ends_at = parse_datetime(ends_at) if isinstance(ends_at, str) else ends_at
        if not starts_at or not ends_at or ends_at <= starts_at:
            raise ValidationError("Booking end time must be after start time")
        if starts_at <= timezone.now():
            raise ValidationError("Bookings must start in the future")
        return starts_at, ends_at

    def _direct_use_window(self, starts_at, ends_at):
        starts_at = parse_datetime(starts_at) if isinstance(starts_at, str) else starts_at
        ends_at = parse_datetime(ends_at) if isinstance(ends_at, str) else ends_at
        now = timezone.now()
        if not starts_at or not ends_at or ends_at <= starts_at:
            raise ValidationError("Booking end time must be after start time")
        if ends_at <= now:
            raise ValidationError("Direct resource use cannot be recorded after it has ended")
        return starts_at, ends_at

    def _assert_capacity(self, resource_item, starts_at, ends_at, quantity, exclude=None):
        resource_item = ResourceItem.objects.select_for_update().get(pk=resource_item.pk)
        if resource_item.kind == ResourceItem.Kind.CONSUMABLE:
            raise ResourceConflict(
                {
                    "code": "consumable_not_bookable",
                    "detail": "Consumables are issued from stock and cannot be booked",
                }
            )
        if resource_item.status != ResourceItem.Status.AVAILABLE:
            raise ResourceConflict(
                {
                    "code": "resource_unusable",
                    "detail": "Resource is not available for new use",
                }
            )
        if (
            resource_item.next_calibration_at
            and resource_item.next_calibration_at <= starts_at.date()
        ):
            raise ResourceConflict(
                {
                    "code": "calibration_due",
                    "detail": "Resource calibration is due before this booking",
                }
            )
        maintenance_conflict = resource_item.maintenance_records.filter(
            takes_offline=True,
            status__in=[
                ResourceMaintenanceRecord.Status.SCHEDULED,
                ResourceMaintenanceRecord.Status.IN_PROGRESS,
            ],
            scheduled_at__lt=ends_at,
        ).filter(Q(due_at__isnull=True) | Q(due_at__gt=starts_at))
        if maintenance_conflict.exists():
            raise ResourceConflict(
                {
                    "code": "resource_maintenance_conflict",
                    "detail": "Resource is unavailable during scheduled maintenance",
                }
            )
        if quantity > resource_item.total_quantity:
            raise ResourceConflict(
                {
                    "code": "insufficient_capacity",
                    "availableQuantity": resource_item.total_quantity,
                    "requestedQuantity": quantity,
                }
            )
        overlapping = Booking.objects.filter(
            resource_item=resource_item,
            status__in=[Booking.Status.CONFIRMED, Booking.Status.RESERVED],
            starts_at__lt=ends_at,
            ends_at__gt=starts_at,
        )
        if exclude is not None:
            overlapping = overlapping.exclude(pk=exclude)
        used = overlapping.aggregate(total=Sum("quantity"))["total"] or 0
        available = max(resource_item.total_quantity - used, 0)
        if quantity > available:
            raise ResourceConflict(
                {
                    "code": "insufficient_capacity",
                    "availableQuantity": available,
                    "requestedQuantity": quantity,
                }
            )

    @transaction.atomic
    def create_booking(
        self, *, resource_item, starts_at, ends_at, quantity=1, purpose: str = "", project=None
    ) -> Booking:
        self._require_active_user()
        is_student = _is_active_student(self.user)
        is_manager = _is_resource_manager(self.user)
        starts_at, ends_at = (
            self._window(starts_at, ends_at)
            if is_student or not is_manager
            else self._direct_use_window(starts_at, ends_at)
        )
        if quantity < 1:
            raise ValidationError({"quantity": "Quantity must be at least 1"})
        if resource_item.status != ResourceItem.Status.AVAILABLE:
            raise ValidationError("Resource is not available for new use")
        policy = resource_item.effective_confirmation_policy
        status = (
            Booking.Status.PENDING
            if is_student and policy == ResourceType.ConfirmationPolicy.APPROVAL_REQUIRED
            else Booking.Status.CONFIRMED
        )
        origin = (
            Booking.Origin.STUDENT_REQUEST
            if is_student
            else (Booking.Origin.STAFF_DIRECT if is_manager else Booking.Origin.LEGACY_BOOKING)
        )
        self._assert_capacity(resource_item, starts_at, ends_at, quantity)
        booking = Booking.objects.create(
            project=project or self.project,
            resource_item=resource_item,
            requested_by=self.user,
            starts_at=starts_at,
            ends_at=ends_at,
            quantity=quantity,
            origin=origin,
            confirmation_policy=policy,
            status=status,
            purpose=purpose,
        )
        record_event(
            None,
            self.user,
            "booking.created",
            f"Created booking {booking.id}",
            booking,
            target_snapshot=_booking_snapshot(booking, outcome="created"),
        )
        self._notify_booking_change(booking, f"Booking {status}")
        return booking

    @transaction.atomic
    def update_booking(
        self,
        booking: Booking,
        *,
        starts_at=None,
        ends_at=None,
        quantity=None,
        purpose: str | None = None,
        version=None,
    ) -> Booking:
        self._require_active_user()
        self._ensure_future_booking(booking)
        if booking.requested_by_id != self.user.id and not _is_resource_manager(self.user):
            raise ValidationError("Only the requester or an advisor can change this booking")
        if version is not None and version != booking.version:
            raise ResourceConflict(
                {"code": "stale_booking_version", "currentVersion": booking.version}
            )
        starts_at, ends_at = self._window(
            starts_at or booking.starts_at, ends_at or booking.ends_at
        )
        quantity = quantity or booking.quantity
        if booking.status in {Booking.Status.CONFIRMED, Booking.Status.RESERVED}:
            self._assert_capacity(booking.resource_item, starts_at, ends_at, quantity, booking.pk)
        booking.starts_at = starts_at
        booking.ends_at = ends_at
        booking.quantity = quantity
        if purpose is not None:
            booking.purpose = purpose
        booking.version += 1
        booking.save()
        self._notify_booking_change(booking, "Booking changed")
        record_event(None, self.user, "booking.changed", f"Changed booking {booking.id}", booking)
        return booking

    @transaction.atomic
    def cancel_booking(self, booking: Booking) -> Booking:
        self._require_active_user()
        booking = Booking.objects.select_for_update().get(pk=booking.pk)
        self._ensure_future_booking(booking)
        if booking.requested_by_id != self.user.id and not _is_resource_manager(self.user):
            raise ValidationError("Only the requester or an advisor can cancel this booking")
        if booking.status not in {
            Booking.Status.PENDING,
            Booking.Status.CONFIRMED,
            Booking.Status.RESERVED,
        }:
            raise ResourceConflict(
                {
                    "code": "stale_decision",
                    "currentStatus": booking.status,
                    "detail": "Only pending or confirmed bookings can be cancelled",
                }
            )
        prior_status = booking.status
        booking.status = Booking.Status.CANCELLED
        booking.cancelled_at = timezone.now()
        booking.version += 1
        booking.save(update_fields=["status", "cancelled_at", "version", "updated_at"])
        self._notify_booking_change(booking, "Booking cancelled")
        record_event(
            None,
            self.user,
            "booking.cancelled",
            f"Cancelled booking {booking.id}",
            booking,
            target_snapshot=_booking_snapshot(
                booking, outcome="cancelled", prior_status=prior_status
            ),
        )
        return booking

    @transaction.atomic
    def return_booking(self, booking: Booking) -> Booking:
        self._require_active_user()
        booking = Booking.objects.select_for_update().get(pk=booking.pk)
        now = timezone.now()
        if booking.requested_by_id != self.user.id and not _is_resource_manager(self.user):
            raise ValidationError("Only the requester or an advisor can return this resource")
        if booking.status not in {Booking.Status.CONFIRMED, Booking.Status.RESERVED}:
            raise ResourceConflict(
                {
                    "code": "return_not_allowed",
                    "currentStatus": booking.status,
                    "detail": "Only active confirmed or reserved bookings can be returned",
                }
            )
        if not (booking.starts_at <= now < booking.ends_at):
            raise ResourceConflict(
                {
                    "code": "return_window_invalid",
                    "currentStatus": booking.status,
                    "detail": "Resources can only be returned during the active use window",
                }
            )
        prior_status = booking.status
        booking.ends_at = now
        booking.status = Booking.Status.COMPLETED
        booking.completed_at = now
        booking.version += 1
        booking.save(update_fields=["ends_at", "status", "completed_at", "version", "updated_at"])
        self._notify_booking_change(booking, "Resource returned")
        record_event(
            None,
            self.user,
            "booking.returned",
            f"Returned booking {booking.id}",
            booking,
            target_snapshot=_booking_snapshot(
                booking, outcome="returned", prior_status=prior_status
            ),
        )
        return booking

    def decide_booking(self, booking: Booking, *, approve: bool, decision_note: str = ""):
        self._require_manager()
        try:
            with transaction.atomic():
                booking = Booking.objects.select_for_update().get(pk=booking.pk)
                if booking.status != Booking.Status.PENDING:
                    raise ResourceConflict(
                        {
                            "code": "duplicate_decision",
                            "currentStatus": booking.status,
                            "detail": "Only pending bookings can be decided",
                        }
                    )
                prior_status = booking.status
                if approve:
                    self._assert_capacity(
                        booking.resource_item, booking.starts_at, booking.ends_at, booking.quantity
                    )
                    booking.status = Booking.Status.CONFIRMED
                else:
                    booking.status = Booking.Status.REJECTED
                booking.reviewer = self.user
                booking.decision_note = decision_note.strip()
                booking.decided_at = timezone.now()
                booking.version += 1
                booking.save()
                record_event(
                    None,
                    self.user,
                    f"booking.{booking.status}",
                    f"Booking {booking.status}",
                    booking,
                    target_snapshot=_booking_snapshot(
                        booking, outcome=booking.status, prior_status=prior_status
                    ),
                )
        except ResourceConflict as exc:
            fresh_booking = Booking.objects.get(pk=booking.pk)
            event_type = (
                "booking.capacity_conflict"
                if exc.payload.get("code") == "insufficient_capacity"
                else "booking.duplicate_decision"
            )
            outcome = (
                "capacity_conflict"
                if exc.payload.get("code") == "insufficient_capacity"
                else "duplicate_decision"
            )
            record_event(
                fresh_booking.project,
                self.user,
                event_type,
                f"Decision conflict for booking {fresh_booking.id}",
                fresh_booking,
                target_snapshot={
                    **_booking_snapshot(fresh_booking, outcome=outcome),
                    **exc.payload,
                },
            )
            raise
        self._notify_booking_change(booking, f"Booking {booking.status}")
        return booking

    def _notify_booking_change(self, booking: Booking, subject: str) -> None:
        try:
            Notification.objects.create(
                project=None,
                recipient=booking.requested_by,
                event_type=Notification.EventType.BOOKING_CHANGED,
                target_type="Booking",
                target_id=str(booking.id),
                subject=subject,
                action_path=f"/resources?booking={booking.id}",
                sender=self.user,
                eligible_at=timezone.now(),
            )
        except Exception:
            # Notification delivery is deliberately best-effort and never owns booking state.
            return
