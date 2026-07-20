from datetime import datetime, timedelta
from zoneinfo import ZoneInfo

from django.db.models import Q
from django.utils import timezone

from apps.projects.models import ProjectMembership, ResearchProject
from apps.projects.services import projects_visible_to
from apps.resources.models import Booking
from apps.submissions.models import ProjectReportSchedule, WeeklyProgressReport
from apps.tasks.models import Task

from .models import ScheduleItem
from .recurrence import expand_occurrences

SOURCE_TYPES = {"schedule", "project", "task", "report", "booking"}


def aggregate_calendar_occurrences(user, starts_at, ends_at, sources=None):
    selected = set(sources or SOURCE_TYPES) & SOURCE_TYPES
    adapters = {
        "schedule": authored_schedule_occurrences,
        "project": project_milestone_occurrences,
        "task": task_deadline_occurrences,
        "report": report_occurrences,
        "booking": booking_occurrences,
    }
    occurrences = []
    for source in SOURCE_TYPES:
        if source in selected:
            occurrences.extend(adapters[source](user, starts_at, ends_at))
    unique = {item["occurrenceId"]: item for item in occurrences}
    return sorted(unique.values(), key=_sort_key)


def authored_schedule_occurrences(user, starts_at, ends_at):
    visible = ScheduleItem.objects.filter(owner=user)
    visible |= ScheduleItem.objects.filter(
        scope=ScheduleItem.Scope.GROUP,
        recipient_grants__recipient=user,
        recipient_grants__valid_from__lt=ends_at,
    ).filter(
        Q(recipient_grants__valid_until__isnull=True)
        | Q(recipient_grants__valid_until__gt=starts_at)
    )
    if getattr(user, "is_administrator", False):
        visible |= ScheduleItem.objects.filter(scope=ScheduleItem.Scope.GROUP)
    output = []
    for item in (
        visible.distinct()
        .select_related("organizer")
        .prefetch_related("recipient_grants", "exceptions")
    ):
        generated = expand_occurrences(
            starts_at=item.starts_at,
            ends_at=item.ends_at,
            starts_on=item.starts_on,
            ends_on=item.ends_on,
            timezone_name=item.timezone,
            frequency=item.recurrence_frequency,
            interval=item.recurrence_interval,
            weekdays=item.recurrence_weekdays,
            until=item.recurrence_until,
            window_start=starts_at,
            window_end=ends_at,
        )
        for occurrence in generated:
            exception = next(
                (
                    candidate
                    for candidate in item.exceptions.all()
                    if (item.all_day and candidate.original_starts_on == occurrence.starts_on)
                    or (not item.all_day and candidate.original_starts_at == occurrence.starts_at)
                ),
                None,
            )
            if (
                exception
                and exception.status == "cancelled"
                and item.scope == ScheduleItem.Scope.PERSONAL
            ):
                continue
            starts_at = (
                exception.override_starts_at
                if exception and exception.override_starts_at
                else occurrence.starts_at
            )
            ends_at = (
                exception.override_ends_at
                if exception and exception.override_ends_at
                else occurrence.ends_at
            )
            starts_on = (
                exception.override_starts_on
                if exception and exception.override_starts_on
                else occurrence.starts_on
            )
            ends_on = (
                exception.override_ends_on
                if exception and exception.override_ends_on
                else occurrence.ends_on
            )
            occurrence_time = starts_at or timezone.make_aware(
                datetime.combine(starts_on, datetime.min.time())
            )
            if (
                item.scope == ScheduleItem.Scope.GROUP
                and item.owner_id != user.id
                and not getattr(user, "is_administrator", False)
                and not any(
                    grant.recipient_id == user.id
                    and grant.valid_from <= occurrence_time
                    and (grant.valid_until is None or grant.valid_until > occurrence_time)
                    for grant in item.recipient_grants.all()
                )
            ):
                continue
            key = (
                occurrence.starts_on.isoformat()
                if item.all_day
                else occurrence.starts_at.isoformat()
            )
            output.append(
                _occurrence(
                    occurrence_id=f"schedule:{item.id}:{key}",
                    source_type="schedule",
                    source_id=item.id,
                    scope=item.scope,
                    category=item.category,
                    title=exception.override_title
                    if exception and exception.override_title is not None
                    else item.title,
                    description=exception.override_description
                    if exception and exception.override_description is not None
                    else item.description,
                    starts_at=starts_at,
                    ends_at=ends_at,
                    starts_on=starts_on,
                    ends_on=ends_on,
                    timezone_name=item.timezone,
                    status=(
                        "completed"
                        if exception and exception.status == "completed"
                        else "cancelled"
                        if exception and exception.status == "cancelled"
                        else item.status
                    ),
                    version=item.version,
                    capabilities={
                        "canView": True,
                        "canEdit": item.owner_id == user.id
                        or (item.scope == "group" and getattr(user, "is_administrator", False)),
                        "canDelete": item.scope == "personal" and item.owner_id == user.id,
                        "canPublish": item.scope == "personal" and item.owner_id == user.id,
                        "canCancel": item.scope == "group"
                        and (item.owner_id == user.id or getattr(user, "is_administrator", False)),
                        "canViewDeliveryStatus": item.scope == "group"
                        and (item.owner_id == user.id or getattr(user, "is_administrator", False)),
                        "isReadOnly": item.owner_id != user.id,
                    },
                )
            )
    return output


def project_milestone_occurrences(user, starts_at, ends_at):
    projects = projects_visible_to(user)
    output = []
    for project in projects:
        for label, value in (("start", project.starts_on), ("deadline", project.ends_on)):
            if value and starts_at.date() <= value < ends_at.date():
                output.append(
                    _occurrence(
                        occurrence_id=f"project:{project.id}:{label}",
                        source_type="project",
                        source_id=project.id,
                        category="project",
                        title=f"{project.title}: {label}",
                        starts_on=value,
                        ends_on=value + timedelta(days=1),
                        status="active" if project.status == "active" else "completed",
                        action_path=f"/projects/{project.id}",
                    )
                )
    return output


def task_deadline_occurrences(user, starts_at, ends_at):
    visible_projects = projects_visible_to(user).values("id")
    tasks = Task.objects.filter(
        project_id__in=visible_projects,
        deadline_at__gte=starts_at,
        deadline_at__lt=ends_at,
    )
    if getattr(user, "global_role", None) == "student":
        tasks = tasks.filter(Q(assignees=user) | Q(assignee=user))
    return [
        _occurrence(
            occurrence_id=f"task:{task.id}:{task.deadline_at.isoformat()}",
            source_type="task",
            source_id=task.id,
            category="task",
            title=task.title,
            description=task.description,
            starts_at=task.deadline_at,
            ends_at=task.deadline_at + timedelta(minutes=30),
            status=task.status,
            action_path=f"/projects/{task.project_id}?task={task.id}",
        )
        for task in tasks.distinct()
    ]


def report_occurrences(user, starts_at, ends_at):
    visible_projects = projects_visible_to(user)
    reports = WeeklyProgressReport.objects.filter(
        project__in=visible_projects,
        report_week_start__gte=starts_at.date(),
        report_week_start__lt=ends_at.date(),
    )
    if getattr(user, "global_role", None) == "student":
        reports = reports.filter(student=user)
    output = [
        _occurrence(
            occurrence_id=f"report:submitted:{report.id}",
            source_type="report",
            source_id=report.id,
            category="report",
            title=f"Weekly report: {report.report_week_start.isoformat()}",
            starts_on=report.report_week_start,
            ends_on=report.report_week_start + timedelta(days=1),
            status="completed",
            action_path=f"/projects/{report.project_id}/reports",
        )
        for report in reports
    ]
    active_projects = visible_projects.filter(status=ResearchProject.Status.ACTIVE)
    if getattr(user, "global_role", None) in {"advisor", "admin"}:
        active_project_ids = active_projects.values("id")
    else:
        active_project_ids = ProjectMembership.objects.filter(
            project__in=active_projects,
            user=user,
            status=ProjectMembership.Status.ACTIVE,
        ).values("project_id")
    policies = ProjectReportSchedule.objects.filter(
        project_id__in=active_project_ids
    ).select_related("project")
    for policy in policies:
        zone = ZoneInfo(policy.timezone)
        current = starts_at.astimezone(zone).date()
        last = ends_at.astimezone(zone).date()
        while current <= last:
            if current.isoweekday() == policy.weekday:
                due_local = datetime.combine(current, policy.deadline_time, tzinfo=zone)
                due = due_local.astimezone(ZoneInfo("UTC"))
                if starts_at <= due < ends_at:
                    output.append(
                        _occurrence(
                            occurrence_id=f"report:due:{policy.id}:{current.isoformat()}",
                            source_type="report",
                            source_id=policy.id,
                            category="report",
                            title=f"{policy.project.title}: weekly report due",
                            starts_at=due,
                            ends_at=due + timedelta(minutes=30),
                            timezone_name=policy.timezone,
                            status="pending",
                            action_path=f"/projects/{policy.project_id}/reports",
                        )
                    )
            current += timedelta(days=1)
    return output


def booking_occurrences(user, starts_at, ends_at):
    bookings = Booking.objects.filter(starts_at__lt=ends_at, ends_at__gt=starts_at)
    if getattr(user, "global_role", None) not in {"advisor", "admin"}:
        bookings = bookings.filter(requested_by=user)
    return [
        _occurrence(
            occurrence_id=f"booking:{booking.id}:{booking.starts_at.isoformat()}",
            source_type="booking",
            source_id=booking.id,
            category="booking",
            title=booking.resource_item.name,
            description=booking.purpose,
            starts_at=booking.starts_at,
            ends_at=booking.ends_at,
            status=booking.status,
            action_path="/resources",
        )
        for booking in bookings.select_related("resource_item")
    ]


def _occurrence(
    *,
    occurrence_id,
    source_type,
    source_id,
    category,
    title,
    status,
    scope="system",
    description="",
    starts_at=None,
    ends_at=None,
    starts_on=None,
    ends_on=None,
    timezone_name="UTC",
    action_path=None,
    version=None,
    capabilities=None,
):
    return {
        "occurrenceId": occurrence_id,
        "sourceType": source_type,
        "sourceId": str(source_id),
        "scheduleId": source_id if source_type == "schedule" else None,
        "scope": scope,
        "category": category,
        "title": title,
        "description": description,
        "allDay": starts_on is not None,
        "startsAt": starts_at,
        "endsAt": ends_at,
        "startsOn": starts_on,
        "endsOn": ends_on,
        "timezone": timezone_name,
        "status": status,
        "actionPath": action_path,
        "version": version,
        "capabilities": capabilities
        or {
            "canView": True,
            "canEdit": False,
            "canDelete": False,
            "canPublish": False,
            "canCancel": False,
            "canViewDeliveryStatus": False,
            "isReadOnly": True,
        },
    }


def _sort_key(item):
    if item["startsAt"]:
        return item["startsAt"]
    return timezone.make_aware(datetime.combine(item["startsOn"], datetime.min.time()))
