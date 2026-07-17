from django.contrib.auth import get_user_model
from django.core.files.base import ContentFile
from django.core.files.storage import default_storage
from django.core.management import call_command
from django.core.management.base import BaseCommand
from django.utils import timezone

from apps.library.models import DocumentCategory, PaperAttachment, PaperRecord
from apps.notifications.models import Notification
from apps.projects.models import ProjectMembership, ResearchProject
from apps.repositories.models import CodeArtifact, CodeArtifactVersion
from apps.resources.models import Booking, ResourceItem, ResourceType
from apps.submissions.models import InlineComment, WeeklyProgressReport
from apps.tasks.models import Task


def _replace_seed_file(storage_key: str, content: bytes) -> int:
    if default_storage.exists(storage_key):
        default_storage.delete(storage_key)
    default_storage.save(storage_key, ContentFile(content))
    return len(content)


class Command(BaseCommand):
    help = "Reset and seed deterministic data for full-stack Playwright tests."

    def add_arguments(self, parser):
        parser.add_argument(
            "--skip-migrate",
            action="store_true",
            help="Skip the pre-seed migration step. Intended only for tests.",
        )

    def handle(self, *args, **options):
        if not options["skip_migrate"]:
            call_command("migrate", interactive=False, verbosity=options["verbosity"])
        call_command("flush", interactive=False, verbosity=0)
        user_model = get_user_model()

        user_model.objects.create_user(
            email="admin@gradsync.local",
            password="password123",
            name="Admin User",
            global_role="admin",
        )
        advisor = user_model.objects.create_user(
            email="advisor@example.edu",
            password="password123",
            name="Advisor User",
            global_role="advisor",
        )
        student = user_model.objects.create_user(
            email="student@example.edu",
            password="password123",
            name="Student User",
            global_role="student",
        )

        today = timezone.localdate()
        project = ResearchProject.objects.create(
            title="Graphene Lab",
            description="Research operations validation",
            advisor=advisor,
            starts_on=today,
            ends_on=today + timezone.timedelta(days=30),
        )
        ProjectMembership.objects.create(project=project, user=advisor, role="advisor")
        ProjectMembership.objects.create(project=project, user=student, role="student")
        DocumentCategory.objects.create(
            name="Protocols",
            description="Shared research protocols",
            created_by=advisor,
        )
        DocumentCategory.objects.create(
            name="Reports",
            description="Project reports and supporting documents",
            created_by=advisor,
        )

        task = Task.objects.create(
            project=project,
            title="Analyze sample",
            description="Validate project isolation and task state.",
            assignee=student,
            created_by=advisor,
            priority="high",
            status="in_progress",
            deadline_at=timezone.now() + timezone.timedelta(days=1),
        )
        Task.objects.create(
            project=project,
            title="Prepare figure",
            assignee=student,
            created_by=advisor,
            parent_task=task,
            priority="high",
            deadline_at=timezone.now() + timezone.timedelta(hours=12),
        )

        report = WeeklyProgressReport.objects.create(
            project=project,
            student=student,
            report_week_start=today,
            completed_work="Completed experiments",
            blockers="",
            next_steps="Write results",
        )
        InlineComment.objects.create(
            project=project,
            target_type="progress_report",
            target_id=report.id,
            anchor="summary",
            body="Add quantified results.",
            author=advisor,
        )

        microscope_type = ResourceType.objects.create(
            name="Microscope",
            field_schema=[
                {
                    "key": "room",
                    "label": "Room",
                    "fieldType": "text",
                    "required": False,
                }
            ],
        )
        resource = ResourceItem.objects.create(
            resource_type=microscope_type,
            name="Confocal microscope",
            location="Room 2",
            field_values={"room": "Room 2"},
        )
        bench_type = ResourceType.objects.create(name="Bench", field_schema=[])
        ResourceItem.objects.create(
            resource_type=bench_type,
            name="Open bench",
            location="Room 3",
        )
        Booking.objects.create(
            project=project,
            resource_item=resource,
            requested_by=student,
            starts_at=timezone.now() + timezone.timedelta(days=2),
            ends_at=timezone.now() + timezone.timedelta(days=2, hours=1),
            purpose="Microscopy",
        )

        Notification.objects.create(
            project=project,
            recipient=advisor,
            sender=student,
            event_type=Notification.EventType.PENDING_REVIEW,
            target_type="WeeklyProgressReport",
            target_id=str(report.id),
            subject="Pending review reminder",
            action_path=f"/projects/{project.id}/reviews",
            eligible_at=timezone.now(),
        )
        paper = PaperRecord.objects.create(
            project=project,
            title="Graph Neural Methods",
            authors=["Lin Chen"],
            tags=["graph"],
            import_source=PaperRecord.ImportSource.LOCAL_FOLDER,
            source_path_label="team-library/papers",
            fingerprint="graph neural methods|lin chen|",
            created_by=advisor,
        )
        paper_bytes = b"%PDF-1.4\n% GradSync e2e seeded paper\n%%EOF\n"
        PaperAttachment.objects.create(
            paper=paper,
            project=project,
            storage_key="e2e/graph.pdf",
            filename="graph.pdf",
            content_type="application/pdf",
            size_bytes=_replace_seed_file("e2e/graph.pdf", paper_bytes),
            checksum_sha256="a" * 64,
            relative_path="papers/graph.pdf",
            imported_by=advisor,
        )
        artifact = CodeArtifact.objects.create(
            project=project,
            name="Analysis Toolkit",
            description="Reusable analysis toolkit artifact for full-stack download checks.",
            tags=["analysis", "python"],
            source_path_label="team-library/code/analysis-toolkit",
            created_by=advisor,
        )
        archive_bytes = b"GradSync e2e analysis toolkit archive\n"
        CodeArtifactVersion.objects.create(
            artifact=artifact,
            project=project,
            version_label="v1",
            storage_key="e2e/analysis-toolkit.zip",
            filename="analysis-toolkit.zip",
            content_type="application/zip",
            size_bytes=_replace_seed_file("e2e/analysis-toolkit.zip", archive_bytes),
            checksum_sha256="c" * 64,
            description="Local folder import for the deterministic e2e analysis toolkit.",
            relative_path_manifest=["README.md", "src/analysis.py"],
            imported_by=advisor,
        )
        call_command("cleanup_seeded_code_artifacts", verbosity=options["verbosity"])
        call_command("cleanup_seeded_library_documents", verbosity=options["verbosity"])

        self.stdout.write(
            self.style.SUCCESS(
                "Seeded full-stack e2e users: admin@gradsync.local, "
                "advisor@example.edu, student@example.edu / password123"
            )
        )
