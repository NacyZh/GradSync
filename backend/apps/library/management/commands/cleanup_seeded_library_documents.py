from django.core.management.base import BaseCommand

from apps.library.services.documents import cleanup_seeded_library_documents


class Command(BaseCommand):
    help = "Remove exact known seeded/example document records."

    def add_arguments(self, parser):
        parser.add_argument(
            "--dry-run",
            action="store_true",
            help="Report matches without removing records.",
        )

    def handle(self, *args, **options):
        result = cleanup_seeded_library_documents(dry_run=options["dry_run"])
        action = "Matched" if options["dry_run"] else "Removed"
        self.stdout.write(
            self.style.SUCCESS(
                f"{action} {result.matched if options['dry_run'] else result.removed} "
                f"seeded document example(s)."
            )
        )
