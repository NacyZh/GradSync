import csv
import io
import json
import re
import shutil
import tempfile
import zipfile

from django.conf import settings
from django.core.exceptions import PermissionDenied, ValidationError
from django.core.files.storage import default_storage
from django.db import transaction
from django.db.models import Max
from django.http import FileResponse
from django.utils import timezone

from apps.audit.models import AuditEvent
from apps.audit.services import record_event
from apps.resources.models import Booking
from apps.submissions.models import WeeklyProgressReport
from apps.tasks.models import Task

from .access_services import project_capabilities
from .material_services import backing_record_for, project_material_display_name
from .models import Deliverable, ProjectCloseoutRecord, ProjectMaterial, ResearchProject

PENDING_REPORT_STATES = {
    WeeklyProgressReport.ReviewStatus.PENDING_REVIEW,
    WeeklyProgressReport.ReviewStatus.NEEDS_REVISION,
}
OPEN_TASK_STATES = {
    Task.Status.NOT_STARTED,
    Task.Status.IN_PROGRESS,
    Task.Status.BLOCKED,
    Task.Status.SUBMITTED,
}
ACTIVE_BOOKING_STATES = {Booking.Status.CONFIRMED, Booking.Status.RESERVED}


def _sample(queryset, fields, limit=5):
    return list(queryset.values(*fields)[:limit])


def build_closeout_preflight(*, user, project):
    capabilities = project_capabilities(user, project)
    if not (
        capabilities["canArchiveProject"]
        or capabilities["canSuperviseGovernance"]
    ):
        raise PermissionDenied("Project closeout access is forbidden.")
    now = timezone.now()
    incomplete_tasks = Task.objects.filter(project=project, status__in=OPEN_TASK_STATES)
    pending_reports = WeeklyProgressReport.objects.filter(
        project=project,
        review_status__in=PENDING_REPORT_STATES,
    )
    pending_materials = ProjectMaterial.objects.filter(
        source_project=project,
        classification_state=ProjectMaterial.ClassificationState.PENDING_REVIEW,
    )
    required_deliverables = Deliverable.objects.filter(
        project=project,
        required=True,
    ).exclude(current_status__in=[Deliverable.Status.ACCEPTED, Deliverable.Status.ARCHIVED])
    unreturned_resources = Booking.objects.filter(
        project=project,
        status__in=ACTIVE_BOOKING_STATES,
        starts_at__lte=now,
    )
    open_bookings = Booking.objects.filter(project=project).filter(
        models_q_open_booking(now)
    )
    checks = [
        _check("incompleteTasks", incomplete_tasks, "attention", ["id", "title", "status"]),
        _check(
            "pendingReports",
            pending_reports,
            "attention",
            ["id", "report_week_start", "review_status"],
        ),
        _check(
            "pendingMaterialPermissions",
            pending_materials,
            "blocked",
            ["id", "material_type", "visibility_state"],
        ),
        _check(
            "unacceptedRequiredDeliverables",
            required_deliverables,
            "blocked",
            ["id", "title", "current_status"],
        ),
        _check(
            "unreturnedResources",
            unreturned_resources,
            "blocked",
            ["id", "resource_item_id", "starts_at", "ends_at", "status"],
        ),
        _check(
            "openBookings",
            open_bookings,
            "attention",
            ["id", "resource_item_id", "starts_at", "ends_at", "status"],
        ),
    ]
    latest = project.closeout_records.select_related("archived_by").first()
    return {
        "projectId": project.id,
        "ready": not any(check["severity"] == "blocked" for check in checks),
        "checks": checks,
        "latestCloseout": (
            {
                "archiveVersion": latest.archive_version,
                "archivedAt": latest.archived_at,
                "archivedBy": latest.archived_by.name,
            }
            if latest
            else None
        ),
    }


def models_q_open_booking(now):
    from django.db.models import Q

    return Q(status=Booking.Status.PENDING) | Q(
        status__in=ACTIVE_BOOKING_STATES,
        starts_at__gt=now,
    )


def _check(key, queryset, nonzero_severity, fields):
    count = queryset.count()
    return {
        "key": key,
        "count": count,
        "severity": nonzero_severity if count else "clear",
        "sample": _sample(queryset, fields),
    }


@transaction.atomic
def closeout_and_archive(*, actor, project, dispositions):
    project = ResearchProject.objects.select_for_update().get(pk=project.pk)
    if not project_capabilities(actor, project)["canArchiveProject"]:
        raise PermissionDenied("Project archival is forbidden.")
    if not dispositions["materialsReviewed"]:
        raise ValidationError({"materialsReviewed": "Confirm the material visibility review."})
    if not dispositions["finalPackageConfirmed"]:
        raise ValidationError({"finalPackageConfirmed": "Confirm the final outcomes package."})

    now = timezone.now()
    if dispositions.get("cancelOpenTasks"):
        Task.objects.filter(project=project, status__in=OPEN_TASK_STATES).update(
            status=Task.Status.CANCELLED,
            completed_at=None,
            updated_at=now,
        )
    if dispositions.get("closePendingReports"):
        WeeklyProgressReport.objects.filter(
            project=project,
            review_status__in=PENDING_REPORT_STATES,
        ).update(
            review_status=WeeklyProgressReport.ReviewStatus.CLOSED,
            reviewed_at=now,
        )
    if dispositions.get("cancelOpenBookings"):
        Booking.objects.filter(project=project).filter(models_q_open_booking(now)).update(
            status=Booking.Status.CANCELLED,
            cancelled_at=now,
            updated_at=now,
        )

    preflight = build_closeout_preflight(user=actor, project=project)
    unresolved = {
        check["key"]: check["count"]
        for check in preflight["checks"]
        if check["count"]
    }
    if unresolved:
        raise ValidationError(
            {
                "message": "Resolve or explicitly dispose of every closeout item.",
                "unresolved": [
                    f"{key}:{count}" for key, count in sorted(unresolved.items())
                ],
            }
        )

    version = (
        project.closeout_records.aggregate(max_version=Max("archive_version"))["max_version"] or 0
    ) + 1
    checklist = {check["key"]: check["count"] == 0 for check in preflight["checks"]}
    snapshot = {
        "projectTitle": project.title,
        "advisorId": project.advisor_id,
        "memberCount": project.memberships.filter(status="active").count(),
        "taskCount": project.tasks.count(),
        "reportCount": project.weekly_reports.count(),
        "materialCount": project.materials.count(),
        "deliverableCount": project.deliverables.count(),
    }
    record = ProjectCloseoutRecord.objects.create(
        project=project,
        archive_version=version,
        checklist=checklist,
        dispositions={key: value for key, value in dispositions.items() if key != "notes"},
        snapshot=snapshot,
        notes=dispositions.get("notes", ""),
        archived_by=actor,
    )
    project.status = ResearchProject.Status.ARCHIVED
    project.archived_at = now
    project.save(update_fields=["status", "archived_at", "updated_at"])
    record_event(
        project,
        actor,
        "project.closeout_completed",
        "Project closeout completed and archived",
        record,
        category=AuditEvent.Category.PROJECT_GOVERNANCE,
        target_snapshot={"archiveVersion": version, "status": project.status},
        allowed_snapshot_keys={"archiveVersion", "status"},
    )
    return record


def _csv_bytes(headers, rows):
    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow(headers)
    writer.writerows([_safe_csv_cell(value) for value in row] for row in rows)
    return output.getvalue().encode()


def _safe_csv_cell(value):
    if isinstance(value, str) and value.startswith(("=", "+", "-", "@")):
        return f"'{value}"
    return value


def _safe_name(value):
    cleaned = re.sub(r"[^A-Za-z0-9._ -]+", "_", str(value)).strip(" .")
    return cleaned[:120] or "file"


def _material_file(material):
    record = backing_record_for(material)
    if record is None:
        return None
    if material.material_type == ProjectMaterial.MaterialType.DOCUMENT and record.document_file_id:
        return record.document_file
    if material.material_type == ProjectMaterial.MaterialType.PAPER:
        if record.uploaded_file_id:
            return record.uploaded_file
        attachment = record.attachments.filter(status="active").first()
        if attachment:
            return _StoredAsset(
                attachment.storage_key,
                attachment.filename,
                attachment.content_type,
                attachment.size_bytes,
            )
    if material.material_type == ProjectMaterial.MaterialType.CODE:
        if record.archive_file_id:
            return record.archive_file
        version = record.versions.filter(status="active").first()
        if version:
            return _StoredAsset(
                version.storage_key,
                version.filename,
                version.content_type,
                version.size_bytes,
            )
    return None


class _StoredAsset:
    def __init__(self, stored_name, original_filename, content_type, size_bytes):
        self.stored_name = stored_name
        self.original_filename = original_filename
        self.content_type = content_type
        self.size_bytes = size_bytes


def project_export_response(*, actor, project):
    capabilities = project_capabilities(actor, project)
    if not (capabilities["canManageProject"] or capabilities["canSuperviseGovernance"]):
        raise PermissionDenied("Project export is forbidden.")
    max_files = getattr(settings, "PROJECT_EXPORT_MAX_FILES", 200)
    max_bytes = getattr(settings, "PROJECT_EXPORT_MAX_BYTES", 262_144_000)
    materials = list(
        project.materials.filter(
            classification_state=ProjectMaterial.ClassificationState.ACTIVE
        ).order_by("id")[:max_files]
    )
    included = []
    skipped = []
    total_bytes = 0
    for material in materials:
        asset = _material_file(material)
        if (
            asset is None
            or not asset.stored_name
            or not default_storage.exists(asset.stored_name)
        ):
            skipped.append({"materialId": material.id, "reason": "file_unavailable"})
            continue
        if total_bytes + asset.size_bytes > max_bytes:
            skipped.append({"materialId": material.id, "reason": "package_size_limit"})
            continue
        total_bytes += asset.size_bytes
        included.append((material, asset))

    archive = tempfile.SpooledTemporaryFile(max_size=10 * 1024 * 1024)
    with zipfile.ZipFile(archive, "w", zipfile.ZIP_DEFLATED, allowZip64=True) as package:
        closeout = project.closeout_records.first()
        manifest = {
            "schemaVersion": 1,
            "exportedAt": timezone.now().isoformat(),
            "project": {
                "id": project.id,
                "title": project.title,
                "description": project.description,
                "status": project.status,
                "startsOn": project.starts_on.isoformat() if project.starts_on else None,
                "endsOn": project.ends_on.isoformat() if project.ends_on else None,
            },
            "closeout": (
                {
                    "archiveVersion": closeout.archive_version,
                    "archivedAt": closeout.archived_at.isoformat(),
                    "checklist": closeout.checklist,
                    "snapshot": closeout.snapshot,
                }
                if closeout
                else None
            ),
            "materialFiles": {
                "included": len(included),
                "skipped": skipped,
                "totalBytes": total_bytes,
            },
        }
        package.writestr("manifest.json", json.dumps(manifest, indent=2, ensure_ascii=False))
        package.writestr(
            "members.csv",
            _csv_bytes(
                ["name", "nickname", "email", "role", "status"],
                (
                    [
                        membership.user.name,
                        membership.user.nickname,
                        membership.user.email,
                        membership.role,
                        membership.status,
                    ]
                    for membership in project.memberships.select_related("user").order_by("id")
                ),
            ),
        )
        package.writestr(
            "tasks.csv",
            _csv_bytes(
                ["id", "title", "description", "status", "priority", "deadline"],
                (
                    [
                        task.id,
                        task.title,
                        task.description,
                        task.status,
                        task.priority,
                        task.deadline_at.isoformat() if task.deadline_at else "",
                    ]
                    for task in project.tasks.order_by("id")
                ),
            ),
        )
        package.writestr(
            "reports.csv",
            _csv_bytes(
                [
                    "id",
                    "student",
                    "week",
                    "completed_work",
                    "blockers",
                    "next_steps",
                    "review_status",
                    "revision",
                ],
                (
                    [
                        report.id,
                        report.student.name,
                        report.report_week_start,
                        report.completed_work,
                        report.blockers,
                        report.next_steps,
                        report.review_status,
                        report.revision_number,
                    ]
                    for report in project.weekly_reports.select_related("student").order_by(
                        "report_week_start", "revision_number"
                    )
                ),
            ),
        )
        deliverables = [
            {
                "id": item.id,
                "title": item.title,
                "status": item.current_status,
                "acceptedRevisionId": item.accepted_revision_id,
                "acceptedAt": item.accepted_at.isoformat() if item.accepted_at else None,
                "evidence": [
                    {
                        "type": evidence.source_type_snapshot,
                        "sourceId": evidence.source_id_snapshot,
                        "label": evidence.label_snapshot,
                        "externalUrl": evidence.external_url,
                    }
                    for evidence in (
                        item.accepted_revision.evidence.all()
                        if item.accepted_revision_id
                        else []
                    )
                ],
            }
            for item in project.deliverables.select_related("accepted_revision").prefetch_related(
                "accepted_revision__evidence"
            )
        ]
        package.writestr(
            "final-deliverables.json",
            json.dumps(deliverables, indent=2, ensure_ascii=False),
        )
        package.writestr(
            "materials.csv",
            _csv_bytes(
                ["id", "name", "type", "visibility", "classification"],
                (
                    [
                        material.id,
                        project_material_display_name(material),
                        material.material_type,
                        material.visibility_state,
                        material.classification_state,
                    ]
                    for material in materials
                ),
            ),
        )
        used_names = set()
        for material, asset in included:
            filename = _safe_name(asset.original_filename)
            archive_name = f"materials/{material.id}-{filename}"
            suffix = 2
            while archive_name in used_names:
                archive_name = f"materials/{material.id}-{suffix}-{filename}"
                suffix += 1
            used_names.add(archive_name)
            with default_storage.open(asset.stored_name, "rb") as source:
                with package.open(archive_name, "w") as target:
                    shutil.copyfileobj(source, target, length=1024 * 1024)
    archive.seek(0)
    record_event(
        project,
        actor,
        "project.exported",
        "Project closeout package exported",
        project,
        category=AuditEvent.Category.PROJECT_GOVERNANCE,
        target_snapshot={"materialFiles": len(included), "status": project.status},
        allowed_snapshot_keys={"materialFiles", "status"},
    )
    return FileResponse(
        archive,
        as_attachment=True,
        filename=f"project-{project.id}-{_safe_name(project.title)}.zip",
        content_type="application/zip",
    )
