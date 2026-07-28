from datetime import datetime, time, timedelta
from zoneinfo import ZoneInfo

from django.db import transaction
from django.utils import timezone

from apps.audit.services import record_execution_event
from apps.projects.models import ResearchProject

from .models import ProjectReportSchedule, ReportingPeriod
from .report_template_services import ensure_default_report_template


def _period_deadline(project, starts_on):
    schedule = ProjectReportSchedule.objects.filter(project=project).first()
    if not schedule:
        return timezone.make_aware(
            datetime.combine(starts_on + timedelta(days=6), time.max),
            ZoneInfo("UTC"),
        )
    deadline_date = starts_on
    while deadline_date.isoweekday() != schedule.weekday:
        deadline_date += timedelta(days=1)
    return datetime.combine(
        deadline_date, schedule.deadline_time, tzinfo=ZoneInfo(schedule.timezone)
    )


@transaction.atomic
def open_reporting_period(*, project, starts_on):
    if project.status == ResearchProject.Status.ARCHIVED:
        raise ValueError("Archived projects cannot open reporting periods.")
    existing = ReportingPeriod.objects.filter(project=project, starts_on=starts_on).first()
    if existing:
        return existing
    template_version = ensure_default_report_template(actor=project.advisor, project=project)
    period = ReportingPeriod.objects.create(
        project=project,
        starts_on=starts_on,
        ends_on=starts_on + timedelta(days=7),
        deadline_at=_period_deadline(project, starts_on),
        template_version=template_version,
        generation_key=f"weekly:{project.pk}:{starts_on.isoformat()}",
    )
    record_execution_event(
        project=project,
        actor=None,
        action="report_period.opened",
        target=period,
        state={"status": period.state},
    )
    return period


@transaction.atomic
def close_due_reporting_periods(*, now=None, limit=200):
    current = now or timezone.now()
    periods = list(
        ReportingPeriod.objects.select_for_update()
        .filter(state=ReportingPeriod.State.OPEN, deadline_at__lt=current)
        .order_by("deadline_at")[:limit]
    )
    for period in periods:
        period.state = ReportingPeriod.State.CLOSED
        period.closed_at = current
        period.save(update_fields=["state", "closed_at"])
    return len(periods)


def open_current_reporting_periods(*, starts_on=None, limit=200):
    current_start = starts_on or (
        timezone.localdate() - timedelta(days=timezone.localdate().weekday())
    )
    opened = 0
    for project in ResearchProject.objects.filter(status=ResearchProject.Status.ACTIVE).order_by(
        "id"
    )[:limit]:
        _, created = ReportingPeriod.objects.get_or_create(
            project=project,
            starts_on=current_start,
            defaults={
                "ends_on": current_start + timedelta(days=7),
                "deadline_at": _period_deadline(project, current_start),
                "template_version": ensure_default_report_template(
                    actor=project.advisor, project=project
                ),
                "generation_key": (f"weekly:{project.pk}:{current_start.isoformat()}"),
            },
        )
        opened += int(created)
    return opened
