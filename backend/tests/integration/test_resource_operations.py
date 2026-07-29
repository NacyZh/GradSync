from decimal import Decimal

import pytest
from django.utils import timezone

from apps.notifications.models import Notification
from apps.resources.models import (
    ConsumableStockTransaction,
    ResourceItem,
    ResourceMaintenanceRecord,
)
from apps.resources.services import (
    BookingService,
    ResourceConflict,
    ResourceInventoryService,
    ResourceOperationsService,
    reconcile_resource_operation_alerts,
)
from tests.factories.accounts import UserFactory
from tests.factories.resources import ResourceItemFactory


@pytest.mark.django_db
def test_fault_and_calibration_records_control_equipment_availability():
    advisor = UserFactory(global_role="advisor")
    resource = ResourceItemFactory(
        manager=advisor,
        calibration_interval_days=90,
    )
    service = ResourceOperationsService(advisor)

    fault = service.create_maintenance(
        resource=resource,
        kind=ResourceMaintenanceRecord.Kind.FAULT,
        title="Vacuum pump failure",
        scheduled_at=timezone.now() + timezone.timedelta(days=1),
    )
    resource.refresh_from_db()
    assert resource.status == ResourceItem.Status.UNAVAILABLE

    service.transition_maintenance(
        fault,
        status=ResourceMaintenanceRecord.Status.CANCELLED,
    )
    resource.refresh_from_db()
    assert resource.status == ResourceItem.Status.AVAILABLE

    calibration = service.create_maintenance(
        resource=resource,
        kind=ResourceMaintenanceRecord.Kind.CALIBRATION,
        title="Quarterly calibration",
        scheduled_at=timezone.now(),
    )
    service.transition_maintenance(
        calibration,
        status=ResourceMaintenanceRecord.Status.IN_PROGRESS,
    )
    service.transition_maintenance(
        calibration,
        status=ResourceMaintenanceRecord.Status.COMPLETED,
    )
    resource.refresh_from_db()
    assert resource.status == ResourceItem.Status.AVAILABLE
    assert resource.next_calibration_at == timezone.localdate() + timezone.timedelta(days=90)


@pytest.mark.django_db
def test_consumable_issue_records_cost_and_emits_low_stock_notification():
    advisor = UserFactory(global_role="advisor")
    resource = ResourceItemFactory(
        manager=advisor,
        kind=ResourceItem.Kind.CONSUMABLE,
        stock_on_hand=12,
        reorder_level=5,
        stock_unit="bottle",
        unit_cost=Decimal("18.50"),
    )

    transaction = ResourceOperationsService(advisor).record_stock_transaction(
        resource=resource,
        kind=ConsumableStockTransaction.Kind.ISSUE,
        quantity_delta=-7,
        note="Buffer preparation",
    )

    resource.refresh_from_db()
    assert resource.stock_on_hand == 5
    assert transaction.balance_after == 5
    assert transaction.unit_cost == Decimal("18.50")
    assert Notification.objects.filter(
        recipient=advisor,
        event_type=Notification.EventType.RESOURCE_LOW_STOCK,
        target_id=str(resource.id),
    ).exists()

    with pytest.raises(ResourceConflict) as exc_info:
        ResourceOperationsService(advisor).record_stock_transaction(
            resource=resource,
            kind=ConsumableStockTransaction.Kind.ISSUE,
            quantity_delta=-6,
        )
    assert exc_info.value.payload["code"] == "insufficient_consumable_stock"


@pytest.mark.django_db
def test_consumable_creation_records_an_opening_balance():
    advisor = UserFactory(global_role="advisor")

    resource = ResourceInventoryService(advisor).create_resource(
        name="Pipette tips",
        resource_type="Lab supply",
        kind=ResourceItem.Kind.CONSUMABLE,
        total_quantity=1,
        stock_on_hand=24,
        reorder_level=5,
        stock_unit="box",
        unit_cost=Decimal("31.25"),
    )

    opening = resource.stock_transactions.get()
    assert opening.kind == ConsumableStockTransaction.Kind.ADJUSTMENT
    assert opening.quantity_delta == 24
    assert opening.balance_after == 24
    assert opening.note == "Opening balance"


@pytest.mark.django_db
def test_overdue_calibration_is_reconciled_once():
    advisor = UserFactory(global_role="advisor")
    resource = ResourceItemFactory(
        manager=advisor,
        next_calibration_at=timezone.localdate() - timezone.timedelta(days=1),
    )

    assert reconcile_resource_operation_alerts() == 1
    assert reconcile_resource_operation_alerts() == 0
    resource.refresh_from_db()
    assert resource.status == ResourceItem.Status.UNAVAILABLE
    assert (
        Notification.objects.filter(
            recipient=advisor,
            event_type=Notification.EventType.RESOURCE_MAINTENANCE_DUE,
            target_id=str(resource.id),
        ).count()
        == 1
    )


@pytest.mark.django_db
def test_consumables_cannot_be_reserved_and_students_cannot_read_cost_ledger(api_client):
    advisor = UserFactory(global_role="advisor")
    student = UserFactory(global_role="student")
    resource = ResourceItemFactory(
        manager=advisor,
        kind=ResourceItem.Kind.CONSUMABLE,
        stock_on_hand=10,
        reorder_level=2,
        stock_unit="box",
    )

    with pytest.raises(ResourceConflict) as exc_info:
        BookingService(student)._assert_capacity(
            resource,
            timezone.now() + timezone.timedelta(days=1),
            timezone.now() + timezone.timedelta(days=1, hours=1),
            1,
        )
    assert exc_info.value.payload["code"] == "consumable_not_bookable"

    api_client.force_authenticate(student)
    response = api_client.get(
        "/api/consumable-transactions/",
        {"resourceId": resource.id},
    )
    assert response.status_code == 403
