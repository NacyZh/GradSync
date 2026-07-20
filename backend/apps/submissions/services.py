from django.core.exceptions import PermissionDenied, ValidationError
from django.db import transaction

from apps.audit.services import record_event
from apps.schedules.permissions import can_manage_report_schedule

from .models import ProjectReportSchedule


class ReportScheduleVersionConflict(Exception):
    def __init__(self, current: ProjectReportSchedule):
        self.current = current
        super().__init__("The report schedule changed. Reload the current policy.")


@transaction.atomic
def configure_project_report_schedule(
    *, actor, project, weekday, deadline_time, timezone_name, expected_version=None
):
    if not can_manage_report_schedule(actor, project):
        raise PermissionDenied("You cannot configure this project's report schedule.")
    if project.status != "active":
        raise ValidationError("Archived projects cannot configure report deadlines.")
    current = ProjectReportSchedule.objects.select_for_update().filter(project=project).first()
    if current and expected_version is not None and expected_version != current.version:
        raise ReportScheduleVersionConflict(current)
    if current:
        current.weekday = weekday
        current.deadline_time = deadline_time
        current.timezone = timezone_name
        current.updated_by = actor
        current.version += 1
        current.save()
        policy = current
        action = "updated"
    else:
        if expected_version not in {None, 0}:
            raise ValidationError("No current report schedule exists.")
        policy = ProjectReportSchedule.objects.create(
            project=project,
            weekday=weekday,
            deadline_time=deadline_time,
            timezone=timezone_name,
            updated_by=actor,
        )
        action = "configured"
    record_event(project, actor, f"report_schedule.{action}", f"Report schedule {action}", policy)
    return policy


@transaction.atomic
def remove_project_report_schedule(*, actor, project, expected_version):
    if not can_manage_report_schedule(actor, project):
        raise PermissionDenied("You cannot remove this project's report schedule.")
    current = ProjectReportSchedule.objects.select_for_update().filter(project=project).first()
    if current is None:
        return
    if expected_version != current.version:
        raise ReportScheduleVersionConflict(current)
    policy_id = current.id
    current.delete()
    record_event(
        project,
        actor,
        "report_schedule.removed",
        "Report schedule removed",
        target_snapshot={"policyId": policy_id, "outcome": "removed"},
    )
