from pathlib import Path

from django.conf import settings
from django.core.mail import send_mail
from django.core.management.base import BaseCommand, CommandError
from django.db import connections
from django.db.migrations.executor import MigrationExecutor

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
        if not options["skip_database"]:
            executor = MigrationExecutor(connections["default"])
            unapplied = executor.migration_plan(executor.loader.graph.leaf_nodes())
            if unapplied:
                issues.append(f"{len(unapplied)} database migrations are not applied")

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

        if issues:
            raise CommandError("Production readiness failed:\n- " + "\n- ".join(issues))

        self.stdout.write(self.style.SUCCESS("Production readiness checks passed"))
