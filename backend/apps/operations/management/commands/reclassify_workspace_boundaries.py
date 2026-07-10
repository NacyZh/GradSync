from django.core.management.base import BaseCommand

from apps.library.models.documents import DocumentRecord
from apps.library.models.papers import PaperRecord
from apps.repositories.models import CodeArtifact


class Command(BaseCommand):
    help = "Review or conservatively reclassify shared workspace boundary records."

    def add_arguments(self, parser):
        parser.add_argument("--dry-run", action="store_true", help="Report counts without writes")
        parser.add_argument("--chunk-size", type=int, default=500)

    def handle(self, *args, **options):
        counts = {
            "papers_standalone_shared": PaperRecord.objects.filter(
                boundary_classification="standalone_shared"
            ).count(),
            "papers_project_material": PaperRecord.objects.filter(
                boundary_classification="project_material"
            ).count(),
            "papers_pending_review": PaperRecord.objects.filter(
                boundary_classification="pending_review"
            ).count(),
            "documents_standalone_shared": DocumentRecord.objects.filter(
                boundary_classification="standalone_shared"
            ).count(),
            "documents_project_material": DocumentRecord.objects.filter(
                boundary_classification="project_material"
            ).count(),
            "documents_pending_review": DocumentRecord.objects.filter(
                boundary_classification="pending_review"
            ).count(),
            "code_standalone_shared": CodeArtifact.objects.filter(
                boundary_classification="standalone_shared"
            ).count(),
            "code_project_material": CodeArtifact.objects.filter(
                boundary_classification="project_material"
            ).count(),
            "code_pending_review": CodeArtifact.objects.filter(
                boundary_classification="pending_review"
            ).count(),
        }
        prefix = "DRY-RUN " if options["dry_run"] else ""
        self.stdout.write(
            prefix + " ".join(f"{key}={value}" for key, value in sorted(counts.items()))
        )
        if not options["dry_run"]:
            self.stdout.write(
                self.style.SUCCESS(
                    "No automatic exposure changes applied; "
                    "ambiguous records remain pending review."
                )
            )
