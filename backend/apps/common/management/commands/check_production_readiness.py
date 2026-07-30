from datetime import timedelta
from pathlib import Path

from django.apps import apps
from django.conf import settings
from django.core.mail import send_mail
from django.core.management.base import BaseCommand, CommandError
from django.db import connections, models
from django.db.migrations.executor import MigrationExecutor
from django.utils import timezone

from apps.common.production_checks import collect_production_readiness_issues


class Command(BaseCommand):
    help = "Validate production settings, repo topology, migrations, static files, and SMTP path."

    def add_arguments(self, parser):
        parser.add_argument("--repo-root", default=str(Path(__file__).resolve().parents[5]))
        parser.add_argument("--skip-database", action="store_true")
        parser.add_argument(
            "--skip-repo-files",
            action="store_true",
            help="Skip repository file checks when running inside a minimal runtime image.",
        )
        parser.add_argument("--smtp-probe-to", default="")

    def handle(self, *args, **options):
        repo_root = None if options["skip_repo_files"] else Path(options["repo_root"])
        issues = collect_production_readiness_issues(settings, repo_root)
        warnings = []
        if not options["skip_database"]:
            ResearchProject = apps.get_model("projects", "ResearchProject")
            ProjectMembership = apps.get_model("projects", "ProjectMembership")
            AuditExport = apps.get_model("audit", "AuditExport")
            executor = MigrationExecutor(connections["default"])
            unapplied = executor.migration_plan(executor.loader.graph.leaf_nodes())
            if unapplied:
                issues.append(f"{len(unapplied)} database migrations are not applied")
            held_project_query = ResearchProject.objects.filter(
                governance_state="hold"
            ).order_by("id")
            held_project_count = held_project_query.count()
            held_projects = list(
                held_project_query.values_list("id", "governance_hold_reason")[:25]
            )
            if held_projects:
                summary = ", ".join(
                    f"{project_id}:{reason}" for project_id, reason in held_projects
                )
                omitted = held_project_count - len(held_projects)
                if omitted:
                    summary += f", and {omitted} more"
                warnings.append(
                    f"{held_project_count} project governance holds need operational "
                    f"attention: {summary}"
                )
            conflicting_projects = (
                ProjectMembership.objects.filter(status="active", role="advisor")
                .values("project_id")
                .annotate(total=models.Count("id"))
                .filter(total__gt=1)
                .values_list("project_id", flat=True)[:25]
            )
            conflicts = list(conflicting_projects)
            if conflicts:
                issues.append(
                    "projects have conflicting active primary advisors: "
                    + ", ".join(str(project_id) for project_id in conflicts)
                )
            stale_export_cutoff = timezone.now() - timedelta(minutes=5)
            stale_export_count = AuditExport.objects.filter(
                status__in=["queued", "processing"],
                created_at__lt=stale_export_cutoff,
            ).count()
            if stale_export_count:
                issues.append(
                    f"{stale_export_count} audit exports have remained pending for over 5 minutes"
                )

        static_root = Path(settings.STATIC_ROOT)
        if not static_root.exists():
            issues.append(f"STATIC_ROOT does not exist: {static_root}")

        probe_to = options["smtp_probe_to"] or getattr(settings, "PRODUCTION_SMTP_PROBE_TO", "")
        if probe_to:
            try:
                delivered_count = send_mail(
                    "GradSync production SMTP probe",
                    "This message verifies the GradSync production notification delivery path.",
                    settings.DEFAULT_FROM_EMAIL,
                    [probe_to],
                    fail_silently=False,
                )
                if delivered_count != 1:
                    issues.append("SMTP delivery probe did not accept exactly one message")
            except Exception as exc:
                issues.append(f"SMTP delivery probe failed: {exc}")

        for warning in warnings:
            self.stderr.write(self.style.WARNING(f"Production readiness warning: {warning}"))

        if issues:
            raise CommandError("Production readiness failed:\n- " + "\n- ".join(issues))

        self.stdout.write(self.style.SUCCESS("Production readiness checks passed"))
