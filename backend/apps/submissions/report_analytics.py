import csv
from io import StringIO

from django.core.exceptions import PermissionDenied
from django.db.models import Count

from apps.common.ranges import bounded_date_range
from apps.projects.models import ProjectMembership

from .models import ReportingPeriod, ReportResponse, WeeklyProgressReport

MAX_ANALYTICS_PERIODS = 104


def _require_analytics_access(actor, project):
    membership = project.memberships.filter(user=actor, status="active").first()
    if not membership and not getattr(actor, "is_superuser", False):
        raise PermissionDenied("Project membership is required.")
    return membership


def calculate_report_analytics(*, actor, project, starts_on, ends_on, student_id=None):
    _require_analytics_access(actor, project)
    date_range = bounded_date_range(starts_on, ends_on, maximum_days=MAX_ANALYTICS_PERIODS * 7)
    starts_on, ends_on = date_range.start, date_range.end
    periods = list(
        ReportingPeriod.objects.filter(
            project=project,
            starts_on__gte=starts_on,
            ends_on__lte=ends_on,
        ).order_by("starts_on")[: MAX_ANALYTICS_PERIODS + 1]
    )
    if len(periods) > MAX_ANALYTICS_PERIODS:
        raise ValueError("Analytics cannot exceed 104 reporting periods.")

    students = project.memberships.filter(status="active", role=ProjectMembership.Role.STUDENT)
    if student_id is not None:
        students = students.filter(user_id=student_id)
    student_ids = list(students.values_list("user_id", flat=True))
    reports = WeeklyProgressReport.objects.filter(
        project=project,
        reporting_period__in=periods,
        student_id__in=student_ids,
    )
    latest = {}
    for report in reports.order_by("student_id", "reporting_period_id", "-revision_number"):
        latest.setdefault((report.student_id, report.reporting_period_id), report.id)
    reports = reports.filter(id__in=latest.values())

    report_rows = list(reports.select_related("reporting_period"))
    expected = len(periods) * len(student_ids)
    on_time = sum(not report.submitted_late for report in report_rows)
    late = sum(report.submitted_late for report in report_rows)
    status_counts = dict(
        reports.values_list("review_status").annotate(count=Count("id")).order_by()
    )
    responses = (
        ReportResponse.objects.filter(
            report_id__in=[report.id for report in report_rows],
            template_field__analytics_enabled=True,
            numeric_value__isnull=False,
        )
        .select_related("template_field", "report")
        .order_by("template_field__order", "report__report_week_start")
    )
    grouped = {}
    for response in responses:
        key = response.template_field.key
        item = grouped.setdefault(
            key,
            {
                "key": key,
                "labelEn": response.template_field.label_en,
                "labelZh": response.template_field.label_zh,
                "unit": (
                    "percent" if response.template_field.field_type == "percentage" else "number"
                ),
                "values": [],
                "sourceReportIds": [],
            },
        )
        item["values"].append(float(response.numeric_value))
        item["sourceReportIds"].append(response.report_id)
    metric_series = []
    for item in grouped.values():
        values = item.pop("values")
        item["value"] = sum(values) / len(values) if values else None
        item["population"] = len(values)
        item["missing"] = expected - len(values)
        metric_series.append(item)

    return {
        "range": {"from": starts_on.isoformat(), "to": ends_on.isoformat()},
        "submissionCounts": {
            "expected": expected,
            "onTime": on_time,
            "late": late,
            "missing": max(0, expected - len(report_rows)),
        },
        "reviewCounts": {
            status: status_counts.get(status, 0)
            for status in [
                "pending_review",
                "reviewed",
                "needs_revision",
                "closed",
            ]
        },
        "metricSeries": metric_series,
        "sourceReportIds": [report.id for report in report_rows],
    }


def export_report_analytics_csv(**kwargs):
    analytics = calculate_report_analytics(**kwargs)
    output = StringIO()
    writer = csv.writer(output)
    writer.writerow(
        [
            "metric",
            "label_en",
            "label_zh",
            "value",
            "unit",
            "population",
            "missing",
            "source_report_ids",
        ]
    )
    counts = analytics["submissionCounts"]
    for key in ("expected", "onTime", "late", "missing"):
        writer.writerow([f"submissions.{key}", "", "", counts[key], "count", "", "", ""])
    for metric in analytics["metricSeries"]:
        writer.writerow(
            [
                metric["key"],
                metric["labelEn"],
                metric["labelZh"],
                metric["value"],
                metric["unit"],
                metric["population"],
                metric["missing"],
                "|".join(str(value) for value in metric["sourceReportIds"]),
            ]
        )
    return output.getvalue()
