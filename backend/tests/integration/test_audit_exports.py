import pytest
from django.utils import timezone

from apps.audit.export_services import create_audit_export, generate_audit_export
from apps.audit.models import AuditEvent, AuditExport
from tests.factories.accounts import VerifiedUserFactory


@pytest.mark.django_db
def test_export_high_water_mark_and_generation_are_idempotent(settings, tmp_path):
    settings.MEDIA_ROOT = tmp_path
    admin = VerifiedUserFactory(global_role="admin", active_role="administrator")
    AuditEvent.objects.create(actor=admin, category="material", summary="Included")
    export = create_audit_export(
        requested_by=admin,
        filters={"category": "material"},
    )
    AuditEvent.objects.create(actor=admin, category="material", summary="Too new")

    generate_audit_export(export.id)
    export.refresh_from_db()
    first_file_id = export.file_id
    generate_audit_export(export.id)
    export.refresh_from_db()

    assert export.status == AuditExport.Status.READY
    assert export.exported_count == 1
    assert export.file_id == first_file_id
    assert export.expires_at > timezone.now()
