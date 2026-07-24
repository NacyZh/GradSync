from celery import shared_task
from django.core.files.storage import default_storage
from django.utils import timezone

from .export_services import generate_audit_export
from .models import AuditExport


@shared_task(bind=True, autoretry_for=(Exception,), retry_backoff=True, max_retries=3)
def generate_audit_export_task(self, export_id):
    return str(generate_audit_export(export_id).id)


@shared_task
def expire_audit_exports():
    exports = AuditExport.objects.filter(
        status=AuditExport.Status.READY,
        expires_at__lte=timezone.now(),
    ).select_related("file")
    count = 0
    for export in exports.iterator():
        if export.file and default_storage.exists(export.file.stored_name):
            default_storage.delete(export.file.stored_name)
        export.status = AuditExport.Status.EXPIRED
        export.save(update_fields=["status"])
        count += 1
    return count
