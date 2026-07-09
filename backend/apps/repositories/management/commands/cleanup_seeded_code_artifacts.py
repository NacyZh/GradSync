from django.core.management.base import BaseCommand

from apps.repositories.services import cleanup_seeded_code_artifacts


class Command(BaseCommand):
    help = "Remove exact seeded code artifacts created by validation or e2e seed data."

    def add_arguments(self, parser):
        parser.add_argument(
            "--dry-run",
            action="store_true",
            help="Report matching seeded code samples without deleting them.",
        )

    def handle(self, *args, **options):
        result = cleanup_seeded_code_artifacts(dry_run=options["dry_run"])
        if options["dry_run"]:
            self.stdout.write(f"Seeded code samples matched: {result.matched}")
            return
        self.stdout.write(f"Seeded code samples removed: {result.removed}")
