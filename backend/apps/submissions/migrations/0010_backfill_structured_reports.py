from datetime import UTC, datetime, time, timedelta

from django.db import migrations

DEFAULT_FIELDS = (
    ("completed_work", "Completed work", "已完成工作", "long_text", True, False),
    ("blockers", "Blockers", "阻碍事项", "risk_blocker", False, True),
    ("next_steps", "Next steps", "下一步计划", "long_text", True, False),
    ("progress_percent", "Progress", "进度", "percentage", False, True),
)


def backfill_structured_reports(apps, schema_editor):
    Project = apps.get_model("projects", "ResearchProject")
    ReportTemplate = apps.get_model("submissions", "ReportTemplate")
    ReportTemplateVersion = apps.get_model("submissions", "ReportTemplateVersion")
    ReportTemplateField = apps.get_model("submissions", "ReportTemplateField")
    ReportingPeriod = apps.get_model("submissions", "ReportingPeriod")
    WeeklyReport = apps.get_model("submissions", "WeeklyProgressReport")
    ReportResponse = apps.get_model("submissions", "ReportResponse")

    for project in Project.objects.all().iterator(chunk_size=200):
        template, _ = ReportTemplate.objects.get_or_create(
            project_id=project.id,
            defaults={"name": "Weekly progress", "created_by_id": project.advisor_id},
        )
        version, _ = ReportTemplateVersion.objects.get_or_create(
            project_id=project.id,
            template_id=template.id,
            version_number=1,
            defaults={
                "status": "published",
                "created_by_id": project.advisor_id,
                "published_by_id": project.advisor_id,
                "published_at": project.created_at,
            },
        )
        fields = {}
        for order, (
            key,
            label_en,
            label_zh,
            field_type,
            required,
            analytics_enabled,
        ) in enumerate(DEFAULT_FIELDS):
            field, _ = ReportTemplateField.objects.get_or_create(
                template_version_id=version.id,
                key=key,
                defaults={
                    "label_en": label_en,
                    "label_zh": label_zh,
                    "field_type": field_type,
                    "required": required,
                    "order": order,
                    "analytics_enabled": analytics_enabled,
                    "min_value": 0 if field_type == "percentage" else None,
                    "max_value": 100 if field_type == "percentage" else None,
                },
            )
            fields[key] = field
        if template.active_version_id is None:
            template.active_version_id = version.id
            template.save(update_fields=["active_version"])

        starts = (
            WeeklyReport.objects.filter(project_id=project.id)
            .values_list("report_week_start", flat=True)
            .distinct()
        )
        for starts_on in starts.iterator(chunk_size=200):
            ends_on = starts_on + timedelta(days=7)
            period, _ = ReportingPeriod.objects.get_or_create(
                project_id=project.id,
                starts_on=starts_on,
                defaults={
                    "ends_on": ends_on,
                    "deadline_at": datetime.combine(
                        ends_on - timedelta(days=1), time.max, tzinfo=UTC
                    ),
                    "template_version_id": version.id,
                    "state": "closed",
                    "closed_at": datetime.combine(ends_on, time.min, tzinfo=UTC),
                    "generation_key": f"legacy:{project.id}:{starts_on.isoformat()}",
                },
            )
            reports = WeeklyReport.objects.filter(
                project_id=project.id,
                report_week_start=starts_on,
                reporting_period__isnull=True,
            )
            for report in reports.iterator(chunk_size=500):
                report.reporting_period_id = period.id
                report.template_version_id = version.id
                report.save(update_fields=["reporting_period", "template_version"])
                legacy_values = {
                    "completed_work": report.completed_work,
                    "blockers": report.blockers,
                    "next_steps": report.next_steps,
                }
                ReportResponse.objects.bulk_create(
                    [
                        ReportResponse(
                            project_id=project.id,
                            report_id=report.id,
                            template_field_id=fields[key].id,
                            value=value,
                            numeric_value=(
                                1
                                if key == "blockers" and value
                                else 0
                                if key == "blockers"
                                else None
                            ),
                        )
                        for key, value in legacy_values.items()
                    ],
                    ignore_conflicts=True,
                    batch_size=500,
                )


class Migration(migrations.Migration):
    dependencies = [
        ("submissions", "0009_structured_reporting"),
    ]

    operations = [
        migrations.RunPython(backfill_structured_reports, migrations.RunPython.noop),
    ]
