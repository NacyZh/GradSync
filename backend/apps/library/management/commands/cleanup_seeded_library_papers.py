from django.core.management.base import BaseCommand
from django.db.models import Q

from apps.library.models import PaperRecord

SEEDED_SAMPLE_TITLES = [
    "Graph Neural Methods",
    "Graph Neural Methods for Materials Research",
    "Graph Neural Methods for Research Groups",
]

SEEDED_SOURCE_PATH_LABELS = [
    "team-library/materials-gnn",
    "team-library/papers",
]


class Command(BaseCommand):
    help = "Remove paper records created by validation or e2e seed data."

    def add_arguments(self, parser):
        parser.add_argument(
            "--dry-run",
            action="store_true",
            help="Report matching seeded paper samples without deleting them.",
        )

    def handle(self, *args, **options):
        queryset = PaperRecord.objects.filter(
            Q(title__in=SEEDED_SAMPLE_TITLES)
            | Q(canonical_title__in=SEEDED_SAMPLE_TITLES)
            | Q(source_path_label__in=SEEDED_SOURCE_PATH_LABELS)
            | Q(fingerprint="graph neural methods|lin chen|")
        )
        count = queryset.count()
        if options["dry_run"]:
            self.stdout.write(f"Seeded paper samples matched: {count}")
            return

        queryset.delete()
        self.stdout.write(f"Seeded paper samples removed: {count}")
