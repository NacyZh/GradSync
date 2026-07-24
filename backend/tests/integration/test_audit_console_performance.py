import time

import pytest

from apps.audit.export_services import create_audit_export, generate_audit_export
from apps.audit.models import AuditEvent
from tests.factories.accounts import VerifiedUserFactory


@pytest.mark.django_db
def test_audit_filter_and_bounded_export_at_retention_scale(settings, tmp_path):
    settings.MEDIA_ROOT = tmp_path
    admin = VerifiedUserFactory(global_role="admin", active_role="administrator")
    AuditEvent.objects.bulk_create(
        [
            AuditEvent(
                actor=admin,
                category="material" if index < 10_000 else "other",
                event_type=f"scale.event.{index % 10}",
                summary=f"Scale event {index}",
            )
            for index in range(100_000)
        ],
        batch_size=2_000,
    )

    started = time.monotonic()
    ids = list(
        AuditEvent.objects.filter(category="material")
        .order_by("-created_at", "-id")
        .values_list("id", flat=True)[:100]
    )
    assert len(ids) == 100
    assert time.monotonic() - started < 2

    started = time.monotonic()
    export = create_audit_export(
        requested_by=admin,
        filters={"category": "material"},
    )
    generate_audit_export(export.id)
    export.refresh_from_db()
    assert export.exported_count == 10_000
    assert time.monotonic() - started < 60
