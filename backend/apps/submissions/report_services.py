from decimal import Decimal, InvalidOperation

from django.core.exceptions import PermissionDenied, ValidationError
from django.db import transaction
from django.db.models import Max
from django.utils import timezone

from apps.audit.services import record_event
from apps.common.project_scope import ProjectScopedService
from apps.notifications.models import Notification
from apps.projects.archive_services import ensure_project_writable

from .models import (
    ReportingPeriod,
    ReportResponse,
    ReportTemplateField,
    WeeklyProgressReport,
)
from .review_assignment_services import reviewer_can_access_target


class WeeklyReportService(ProjectScopedService):
    def __init__(self, user, project):
        super().__init__(user)
        self.project = project

    def submit_report(self, **data) -> WeeklyProgressReport:
        self.require_project_member(self.project)
        ensure_project_writable(self.project)
        if not self.project.memberships.filter(
            user=self.user, status="active", role="student"
        ).exists():
            raise PermissionDenied("Only project students can submit weekly reports")
        existing_reports = WeeklyProgressReport.objects.filter(
            project=self.project,
            student=self.user,
            report_week_start=data["report_week_start"],
        ).order_by("-revision_number", "-submitted_at")
        latest = existing_reports.first()
        if latest and latest.review_status != WeeklyProgressReport.ReviewStatus.NEEDS_REVISION:
            raise ValidationError(
                "A weekly report already exists for this project week. "
                "Wait for review or choose a different week."
            )
        report = WeeklyProgressReport.objects.create(
            project=self.project,
            student=self.user,
            revision_number=(latest.revision_number + 1 if latest else 1),
            **data,
        )
        for membership in self.project.memberships.filter(
            role__in=["advisor", "co_advisor"], status="active"
        ):
            Notification.objects.create(
                project=self.project,
                recipient=membership.user,
                event_type=Notification.EventType.NEW_SUBMISSION,
                target_type="WeeklyProgressReport",
                target_id=str(report.id),
                subject="New weekly progress report submitted",
                action_path=f"/projects/{self.project.id}/reports/{report.id}",
                sender=self.user,
                eligible_at=timezone.now(),
            )
        record_event(
            self.project,
            self.user,
            "weekly_report.submitted",
            f"Submitted weekly progress report revision {report.revision_number}",
            report,
        )
        return report

    def update_review_status(
        self, report: WeeklyProgressReport, review_status: str
    ) -> WeeklyProgressReport:
        if not reviewer_can_access_target(user=self.user, target=report):
            raise PermissionDenied("You are not assigned to review this report")
        ensure_project_writable(self.project)
        report.review_status = review_status
        report.reviewed_at = timezone.now()
        report.save(update_fields=["review_status", "reviewed_at"])
        record_event(
            self.project,
            self.user,
            "weekly_report.reviewed",
            f"Set weekly report {report.id} to {review_status}",
            report,
        )
        return report


def _empty_response(value):
    return value is None or value == "" or value == []


def _validate_response_value(field, value, project):
    field_type = field.field_type
    numeric_value = None
    source_type = ""
    source_id = ""
    if field.required and _empty_response(value):
        raise ValueError(f"{field.label_en} is required.")
    if _empty_response(value):
        return value, numeric_value, source_type, source_id
    if field_type == ReportTemplateField.FieldType.LONG_TEXT:
        if not isinstance(value, str) or len(value) > 12000:
            raise ValueError(f"{field.label_en} must be text.")
    elif field_type in {
        ReportTemplateField.FieldType.NUMBER,
        ReportTemplateField.FieldType.PERCENTAGE,
    }:
        try:
            numeric_value = Decimal(str(value))
        except InvalidOperation as exc:
            raise ValueError(f"{field.label_en} must be numeric.") from exc
        if field.min_value is not None and numeric_value < field.min_value:
            raise ValueError(f"{field.label_en} is below its minimum.")
        if field.max_value is not None and numeric_value > field.max_value:
            raise ValueError(f"{field.label_en} exceeds its maximum.")
        value = float(numeric_value)
    elif field_type == ReportTemplateField.FieldType.SINGLE_CHOICE:
        allowed = {option["value"] for option in field.options}
        if value not in allowed:
            raise ValueError(f"Select a valid {field.label_en} option.")
    elif field_type == ReportTemplateField.FieldType.MULTIPLE_CHOICE:
        allowed = {option["value"] for option in field.options}
        if (
            not isinstance(value, list)
            or len(value) != len(set(value))
            or not set(value).issubset(allowed)
        ):
            raise ValueError(f"Select valid {field.label_en} options.")
    elif field_type == ReportTemplateField.FieldType.EXECUTION_PROGRESS:
        if not isinstance(value, dict):
            raise ValueError("Execution progress must select a project record.")
        source_type = str(value.get("sourceType", ""))
        source_id = str(value.get("sourceId", ""))
        if source_type == "milestone":
            exists = project.milestones.filter(pk=source_id).exists()
        elif source_type == "deliverable":
            exists = project.deliverables.filter(pk=source_id).exists()
        else:
            exists = False
        if not exists:
            raise ValueError("Execution source must belong to this project.")
        progress = value.get("progressPercent")
        if progress is not None:
            numeric_value = Decimal(str(progress))
            if not Decimal("0") <= numeric_value <= Decimal("100"):
                raise ValueError("Execution progress must be between 0 and 100.")
    elif field_type == ReportTemplateField.FieldType.RISK_BLOCKER:
        if not isinstance(value, (str, list, dict)):
            raise ValueError("Risk or blocker response is invalid.")
        numeric_value = Decimal(len(value) if isinstance(value, list) else 1 if value else 0)
    return value, numeric_value, source_type, source_id


@transaction.atomic
def submit_structured_report(
    *,
    actor,
    project,
    period: ReportingPeriod,
    responses: dict,
    idempotency_key: str,
):
    if not project.memberships.filter(user=actor, status="active", role="student").exists():
        raise PermissionDenied("Only project students can submit progress reports.")
    ensure_project_writable(project)
    period = (
        ReportingPeriod.objects.select_for_update()
        .select_related("template_version")
        .get(pk=period.pk)
    )
    if period.project_id != project.id:
        raise ValueError("Reporting period must belong to this project.")
    existing = WeeklyProgressReport.objects.filter(
        project=project, student=actor, idempotency_key=idempotency_key
    ).first()
    if existing:
        return existing
    latest = (
        WeeklyProgressReport.objects.filter(
            project=project,
            student=actor,
            reporting_period=period,
        )
        .order_by("-revision_number")
        .first()
    )
    if latest and latest.review_status != WeeklyProgressReport.ReviewStatus.NEEDS_REVISION:
        raise ValueError("This reporting period is awaiting review.")
    fields = list(period.template_version.fields.all())
    known_keys = {field.key for field in fields}
    if set(responses) - known_keys:
        raise ValueError("A response references an unknown template field.")
    prepared = []
    for field in fields:
        value, numeric, source_type, source_id = _validate_response_value(
            field, responses.get(field.key), project
        )
        if not _empty_response(value) or field.required:
            prepared.append((field, value, numeric, source_type, source_id))
    revision_number = (
        WeeklyProgressReport.objects.filter(
            project=project,
            student=actor,
            report_week_start=period.starts_on,
        ).aggregate(value=Max("revision_number"))["value"]
        or 0
    ) + 1
    report = WeeklyProgressReport.objects.create(
        project=project,
        student=actor,
        report_week_start=period.starts_on,
        reporting_period=period,
        template_version=period.template_version,
        completed_work=str(responses.get("completed_work", "")),
        blockers=str(responses.get("blockers", "")),
        next_steps=str(responses.get("next_steps", "")),
        revision_number=revision_number,
        submitted_late=timezone.now() > period.deadline_at,
        idempotency_key=idempotency_key,
    )
    ReportResponse.objects.bulk_create(
        [
            ReportResponse(
                project=project,
                report=report,
                template_field=field,
                value=value,
                numeric_value=numeric,
                source_type=source_type,
                source_id=source_id,
            )
            for field, value, numeric, source_type, source_id in prepared
        ]
    )
    for membership in project.memberships.filter(
        role__in=["advisor", "co_advisor"], status="active"
    ).select_related("user"):
        Notification.objects.create(
            project=project,
            recipient=membership.user,
            event_type=Notification.EventType.NEW_SUBMISSION,
            target_type="WeeklyProgressReport",
            target_id=str(report.id),
            subject="Structured progress report submitted",
            action_path=f"/projects/{project.id}/reviews",
            sender=actor,
            eligible_at=timezone.now(),
            category=Notification.Category.REPORT,
        )
    record_event(
        project,
        actor,
        "weekly_report.structured_submitted",
        f"Submitted structured report revision {report.revision_number}",
        report,
        target_snapshot={
            "status": report.review_status,
            "version": report.response_schema_version,
        },
        allowed_snapshot_keys={"status", "version"},
    )
    return report
