from collections import defaultdict
from datetime import timedelta

from django.db.models import Count, Q
from django.db.models.functions import TruncDate
from django.utils import timezone

from apps.audit.models import AuditEvent
from apps.notifications.models import NotificationDeliveryAttempt
from apps.projects.models import ProjectMembership, ResearchProject
from apps.submissions.models import ReportingPeriod
from apps.tasks.models import Task

DEFAULT_WINDOW_DAYS = 30
TREND_DAYS = 14
LONG_BLOCKED_DAYS = 7


def _percentage(numerator: int, denominator: int) -> float:
    return round((numerator / denominator) * 100, 1) if denominator else 0.0


def _daily_counts(queryset, field: str, dates: list):
    counts = {
        row["day"]: row["count"]
        for row in queryset.annotate(day=TruncDate(field)).values("day").annotate(count=Count("id"))
    }
    return [counts.get(day, 0) for day in dates]


def build_project_health_snapshot(*, now=None, window_days=DEFAULT_WINDOW_DAYS):
    now = now or timezone.now()
    today = timezone.localdate(now)
    window_start = now - timedelta(days=window_days)
    trend_start = today - timedelta(days=TREND_DAYS - 1)
    blocked_before = now - timedelta(days=LONG_BLOCKED_DAYS)

    projects = list(
        ResearchProject.objects.filter(status=ResearchProject.Status.ACTIVE)
        .select_related("advisor")
        .order_by("title")
    )
    project_ids = [project.id for project in projects]

    task_rows = (
        Task.objects.filter(project_id__in=project_ids)
        .exclude(status__in=[Task.Status.COMPLETED, Task.Status.CANCELLED])
        .values("project_id")
        .annotate(
            open_count=Count("id"),
            overdue_count=Count("id", filter=Q(deadline_at__lt=now)),
            blocked_count=Count(
                "id",
                filter=Q(status=Task.Status.BLOCKED, updated_at__lte=blocked_before),
            ),
        )
    )
    task_metrics = {row["project_id"]: row for row in task_rows}
    blocked_task_queryset = Task.objects.filter(
        project_id__in=project_ids,
        status=Task.Status.BLOCKED,
        updated_at__lte=blocked_before,
    )
    blocked_task_count = blocked_task_queryset.count()
    blocked_tasks = list(
        blocked_task_queryset
        .select_related("project")
        .order_by("updated_at", "id")[:50]
    )

    student_counts = {
        row["project_id"]: row["count"]
        for row in ProjectMembership.objects.filter(
            project_id__in=project_ids,
            role=ProjectMembership.Role.STUDENT,
            status=ProjectMembership.Status.ACTIVE,
        )
        .values("project_id")
        .annotate(count=Count("user_id", distinct=True))
    }
    periods = list(
        ReportingPeriod.objects.filter(
            project_id__in=project_ids,
            deadline_at__gte=window_start,
            deadline_at__lt=now,
        )
        .select_related("project")
        .prefetch_related("reports")
        .order_by("deadline_at")
    )
    missing_by_project = defaultdict(int)
    missing_reports = []
    for period in periods:
        expected = student_counts.get(period.project_id, 0)
        submitted = len({report.student_id for report in period.reports.all()})
        missing = max(expected - submitted, 0)
        if not missing:
            continue
        missing_by_project[period.project_id] += missing
        missing_reports.append(
            {
                "projectId": period.project_id,
                "projectTitle": period.project.title,
                "periodId": period.id,
                "periodStart": period.starts_on,
                "deadlineAt": period.deadline_at,
                "missingCount": missing,
                "actionPath": f"/projects/{period.project_id}/reports",
            }
        )

    conflict_events = AuditEvent.objects.filter(
        event_type__in=["booking.capacity_conflict", "booking.resource_conflict"],
        created_at__gte=window_start,
    )
    conflicts_by_project = {
        row["project_id"]: row["count"]
        for row in conflict_events.exclude(project_id=None)
        .values("project_id")
        .annotate(count=Count("id"))
    }
    email_attempts = NotificationDeliveryAttempt.objects.filter(
        channel=NotificationDeliveryAttempt.Channel.EMAIL,
        completed_at__gte=window_start,
    )
    failed_attempts = email_attempts.filter(state=NotificationDeliveryAttempt.State.FAILED)
    failures_by_project = {
        row["notification__project_id"]: row["count"]
        for row in failed_attempts.exclude(notification__project_id=None)
        .values("notification__project_id")
        .annotate(count=Count("id"))
    }

    project_rows = []
    for project in projects:
        tasks = task_metrics.get(project.id, {})
        overdue_project = bool(project.ends_on and project.ends_on < today)
        blocked_count = tasks.get("blocked_count", 0)
        missing_count = missing_by_project.get(project.id, 0)
        held = project.governance_state == ResearchProject.GovernanceState.HOLD
        conflict_count = conflicts_by_project.get(project.id, 0)
        failure_count = failures_by_project.get(project.id, 0)
        score = max(
            0,
            100
            - (25 if overdue_project else 0)
            - min(blocked_count * 10, 30)
            - min(missing_count * 8, 24)
            - (30 if held else 0)
            - min(conflict_count * 5, 15)
            - min(failure_count * 3, 15),
        )
        level = "critical" if score < 50 else "attention" if score < 75 else "healthy"
        project_rows.append(
            {
                "projectId": project.id,
                "title": project.title,
                "advisorName": project.advisor.name,
                "endsOn": project.ends_on,
                "overdue": overdue_project,
                "openTaskCount": tasks.get("open_count", 0),
                "overdueTaskCount": tasks.get("overdue_count", 0),
                "longBlockedTaskCount": blocked_count,
                "missingReportCount": missing_count,
                "governanceState": project.governance_state,
                "governanceHoldReason": project.governance_hold_reason,
                "resourceConflictCount": conflict_count,
                "notificationFailureCount": failure_count,
                "healthScore": score,
                "healthLevel": level,
                "actionPath": f"/projects/{project.id}",
            }
        )
    project_rows.sort(key=lambda row: (row["healthScore"], -row["overdueTaskCount"], row["title"]))

    trend_dates = [trend_start + timedelta(days=index) for index in range(TREND_DAYS)]
    total_email_attempts = email_attempts.count()
    total_failures = failed_attempts.count()
    overdue_projects = sum(1 for project in projects if project.ends_on and project.ends_on < today)
    holds = [project for project in projects if project.governance_state == "hold"]

    return {
        "generatedAt": now,
        "windowDays": window_days,
        "longBlockedDays": LONG_BLOCKED_DAYS,
        "summary": {
            "activeProjects": len(projects),
            "overdueProjects": overdue_projects,
            "overdueProjectRate": _percentage(overdue_projects, len(projects)),
            "longBlockedTasks": blocked_task_count,
            "missingReports": sum(missing_by_project.values()),
            "governanceHolds": len(holds),
            "resourceConflicts": conflict_events.count(),
            "notificationFailures": total_failures,
            "notificationFailureRate": _percentage(total_failures, total_email_attempts),
        },
        "projects": project_rows,
        "blockedTasks": [
            {
                "taskId": task.id,
                "title": task.title,
                "projectId": task.project_id,
                "projectTitle": task.project.title,
                "blockedSince": task.updated_at,
                "blockedDays": max((now - task.updated_at).days, LONG_BLOCKED_DAYS),
                "deadlineAt": task.deadline_at,
                "actionPath": f"/projects/{task.project_id}",
            }
            for task in blocked_tasks
        ],
        "missingReports": missing_reports[:50],
        "governanceHolds": [
            {
                "projectId": project.id,
                "projectTitle": project.title,
                "reason": project.governance_hold_reason,
                "startedAt": project.governance_hold_started_at,
                "actionPath": f"/projects/{project.id}",
            }
            for project in holds
        ],
        "trend": [
            {
                "date": day,
                "resourceConflicts": conflict_count,
                "notificationFailures": failure_count,
            }
            for day, conflict_count, failure_count in zip(
                trend_dates,
                _daily_counts(
                    conflict_events.filter(created_at__date__gte=trend_start),
                    "created_at",
                    trend_dates,
                ),
                _daily_counts(
                    failed_attempts.filter(completed_at__date__gte=trend_start),
                    "completed_at",
                    trend_dates,
                ),
                strict=True,
            )
        ],
    }
