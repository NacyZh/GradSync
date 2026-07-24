import csv
import hashlib
import io
from datetime import timedelta
from uuid import uuid4

from django.conf import settings
from django.core.exceptions import ValidationError
from django.core.files.base import ContentFile
from django.core.files.storage import default_storage
from django.db import transaction
from django.db.models import Q
from django.utils import timezone
from django.utils.dateparse import parse_datetime

from apps.common.models import UploadedFile

from .models import AuditEvent, AuditExport
from .services import record_event, redact_snapshot

ALLOWED_FILTERS = {
    "startsAt",
    "endsAt",
    "actorId",
    "projectId",
    "category",
    "outcome",
    "targetType",
    "targetId",
    "q",
}


def normalize_audit_filters(filters) -> dict:
    normalized = {}
    for key in ALLOWED_FILTERS:
        value = filters.get(key)
        if value in (None, ""):
            continue
        normalized[key] = str(value).strip()[:100]
    return normalized


def audit_queryset(filters, *, high_water_event_id=None):
    queryset = AuditEvent.objects.select_related("actor", "project")
    if high_water_event_id is not None:
        queryset = queryset.filter(id__lte=high_water_event_id)
    if filters.get("startsAt"):
        value = parse_datetime(filters["startsAt"])
        if value:
            queryset = queryset.filter(created_at__gte=value)
    if filters.get("endsAt"):
        value = parse_datetime(filters["endsAt"])
        if value:
            queryset = queryset.filter(created_at__lte=value)
    mappings = {
        "actorId": "actor_id",
        "projectId": "project_id",
        "category": "category",
        "outcome": "outcome",
        "targetType": "target_type",
        "targetId": "target_id",
    }
    for source, target in mappings.items():
        if filters.get(source):
            queryset = queryset.filter(**{target: filters[source]})
    if filters.get("q"):
        query = filters["q"]
        queryset = queryset.filter(
            Q(summary__icontains=query)
            | Q(event_type__icontains=query)
            | Q(target_id__icontains=query)
            | Q(correlation_id__icontains=query)
        )
    return queryset.order_by("-created_at", "-id")


@transaction.atomic
def create_audit_export(*, requested_by, filters):
    normalized = normalize_audit_filters(filters)
    if not normalized:
        raise ValidationError("Select at least one audit filter.")
    high_water = AuditEvent.objects.order_by("-id").values_list("id", flat=True).first() or 0
    count = audit_queryset(normalized, high_water_event_id=high_water).count()
    limit = min(settings.AUDIT_EXPORT_MAX_ROWS, 10_000)
    if count < 1:
        raise ValidationError("No audit events match this export scope.")
    if count > limit:
        raise ValidationError(f"Narrow the export scope to {limit} events or fewer.")
    export = AuditExport.objects.create(
        requested_by=requested_by,
        filter_snapshot=normalized,
        high_water_event_id=high_water,
        requested_count=count,
        expires_at=timezone.now() + timedelta(seconds=settings.AUDIT_EXPORT_TTL_SECONDS),
    )
    record_event(
        None,
        requested_by,
        "audit_access.export_requested",
        "Audit export requested",
        export,
        category=AuditEvent.Category.AUDIT_ACCESS,
        outcome=AuditEvent.Outcome.QUEUED,
        target_snapshot={"status": export.status, "requestedCount": count},
        allowed_snapshot_keys={"status", "requestedCount"},
    )
    return export


@transaction.atomic
def generate_audit_export(export_id):
    export = AuditExport.objects.select_for_update().get(pk=export_id)
    if export.status == AuditExport.Status.READY and export.file_id:
        return export
    export.status = AuditExport.Status.PROCESSING
    export.started_at = export.started_at or timezone.now()
    export.failure_reason = ""
    export.save(update_fields=["status", "started_at", "failure_reason"])
    try:
        output = io.StringIO()
        writer = csv.writer(output)
        writer.writerow(
            [
                "id",
                "created_at",
                "category",
                "outcome",
                "event_type",
                "actor_id",
                "project_id",
                "target_type",
                "target_id",
                "summary",
                "correlation_id",
                "actor_snapshot",
                "target_snapshot",
            ]
        )
        count = 0
        for event in audit_queryset(
            export.filter_snapshot,
            high_water_event_id=export.high_water_event_id,
        ).iterator(chunk_size=500):
            writer.writerow(
                [
                    event.id,
                    event.created_at.isoformat(),
                    event.category,
                    event.outcome,
                    event.event_type,
                    event.actor_id or "",
                    event.project_id or "",
                    event.target_type,
                    event.target_id,
                    event.summary[:1000],
                    event.correlation_id,
                    redact_snapshot(event.actor_snapshot),
                    redact_snapshot(event.target_snapshot),
                ]
            )
            count += 1
        content = output.getvalue().encode()
        checksum = hashlib.sha256(content).hexdigest()
        filename = f"audit-export-{export.id}.csv"
        stored_name = default_storage.save(
            f"audit-exports/{uuid4().hex}.csv",
            ContentFile(content),
        )
        uploaded = UploadedFile.objects.create(
            owner=export.requested_by,
            category=UploadedFile.Category.AUDIT_EXPORT,
            original_filename=filename,
            stored_name=stored_name,
            content_type="text/csv",
            size_bytes=len(content),
            checksum_sha256=checksum,
        )
        export.status = AuditExport.Status.READY
        export.file = uploaded
        export.checksum_sha256 = checksum
        export.exported_count = count
        export.completed_at = timezone.now()
        export.save()
        record_event(
            None,
            export.requested_by,
            "audit_access.export_completed",
            "Audit export completed",
            export,
            category=AuditEvent.Category.AUDIT_ACCESS,
            target_snapshot={"status": export.status, "exportedCount": count},
            allowed_snapshot_keys={"status", "exportedCount"},
        )
    except Exception:
        export.status = AuditExport.Status.FAILED
        export.failure_reason = "Audit export generation failed."
        export.completed_at = timezone.now()
        export.save(update_fields=["status", "failure_reason", "completed_at"])
        raise
    return export
