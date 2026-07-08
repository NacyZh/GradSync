from django.contrib.auth import get_user_model
from django.core.management import call_command
from django.core.management.base import BaseCommand
from django.utils import timezone

from apps.notifications.models import Notification
from apps.projects.models import ProjectMembership, ResearchProject
from apps.repositories.models import CodeArtifact, CodeArtifactVersion
from apps.resources.models import Booking, ResourceItem, ResourceType
from apps.submissions.models import Draft, DraftVersion, InlineComment, WeeklyProgressReport
from apps.tasks.models import Task

VALIDATION_ACCOUNTS = [
    {
        "email": "admin@gradsync.local",
        "name": "System Administrator",
        "global_role": "admin",
        "password": "admin123",
    },
    {
        "email": "advisor@example.com",
        "name": "Research Advisor",
        "global_role": "advisor",
        "password": "advisor123",
    },
    {
        "email": "student@example.com",
        "name": "Graduate Researcher",
        "global_role": "student",
        "password": "student123",
    },
    {
        "email": "reviewer@example.com",
        "name": "Faculty Reviewer",
        "global_role": "advisor",
        "password": "reviewer123",
    },
]


class Command(BaseCommand):
    help = "Seed production-shaped validation data for research operations."

    def handle(self, *args, **options):
        user_model = get_user_model()

        created_users = {}
        for acct in VALIDATION_ACCOUNTS:
            user, created = user_model.objects.get_or_create(
                email=acct["email"],
                defaults={
                    "name": acct["name"],
                    "global_role": acct["global_role"],
                    "status": user_model.Status.ACTIVE,
                },
            )
            user.set_password(acct["password"])
            if acct["email"] == "student@example.com":
                user.locale = "zh"
            user.save(update_fields=["password", "locale"])
            created_users[acct["email"]] = user
            verb = "Created" if created else "Updated"
            self.stdout.write(
                f"  {verb} {acct['global_role']}: {acct['email']} / {acct['password']}"
            )

        advisor = created_users["advisor@example.com"]
        student = created_users["student@example.com"]
        reviewer = created_users["reviewer@example.com"]
        project, _ = ResearchProject.objects.get_or_create(
            title="Graphene Methods Validation",
            defaults={
                "description": "Production-shaped validation project for research operations",
                "advisor": advisor,
                "starts_on": timezone.localdate(),
                "ends_on": timezone.localdate() + timezone.timedelta(days=30),
            },
        )
        for user, role in [(advisor, "advisor"), (student, "student"), (reviewer, "reviewer")]:
            ProjectMembership.objects.update_or_create(
                project=project, user=user, defaults={"role": role, "status": "active"}
            )
        call_command("remove_seeded_paper_samples", verbosity=options["verbosity"])
        call_command("remove_seeded_code_samples", verbosity=options["verbosity"])
        parent, _ = Task.objects.get_or_create(
            project=project,
            title="Prepare manuscript methods section",
            defaults={
                "created_by": advisor,
                "assignee": student,
                "deadline_at": timezone.now() + timezone.timedelta(days=7),
            },
        )
        Task.objects.get_or_create(
            project=project,
            title="Summarize related work",
            defaults={
                "created_by": advisor,
                "assignee": student,
                "parent_task": parent,
                "deadline_at": timezone.now() + timezone.timedelta(days=1),
            },
        )

        equipment_type, _ = ResourceType.objects.get_or_create(
            name="Shared Instrument",
            defaults={
                "description": "Configurable equipment resources for validation",
                "field_schema": [
                    {"key": "room", "label": "Room", "fieldType": "text", "required": True},
                    {
                        "key": "operatorRequired",
                        "label": "Operator required",
                        "fieldType": "boolean",
                    },
                ],
            },
        )
        resource, _ = ResourceItem.objects.get_or_create(
            resource_type=equipment_type,
            name="Confocal Microscope",
            defaults={
                "description": "Shared imaging instrument",
                "location": "Room 101",
                "field_values": {"room": "Room 101", "operatorRequired": True},
            },
        )
        Booking.objects.get_or_create(
            project=project,
            resource_item=resource,
            requested_by=student,
            starts_at=timezone.now() + timezone.timedelta(days=1),
            ends_at=timezone.now() + timezone.timedelta(days=1, hours=1),
            defaults={"purpose": "Microscopy validation session"},
        )

        draft, _ = Draft.objects.get_or_create(
            project=project, student=student, title="Graphene manuscript"
        )
        version, _ = DraftVersion.objects.get_or_create(
            draft=draft,
            project=project,
            version_number=1,
            defaults={"submitted_by": student, "content_reference": "manuscript-v1.pdf"},
        )
        report, _ = WeeklyProgressReport.objects.get_or_create(
            project=project,
            student=student,
            report_week_start=timezone.localdate(),
            defaults={
                "completed_work": "Completed experiment setup",
                "blockers": "",
                "next_steps": "Analyze validation results",
            },
        )
        InlineComment.objects.get_or_create(
            project=project,
            target_type="draft_version",
            target_id=version.id,
            author=advisor,
            anchor="abstract",
            defaults={"body": "Clarify the primary contribution."},
        )
        Notification.objects.get_or_create(
            project=project,
            recipient=advisor,
            sender=student,
            event_type=Notification.EventType.NEW_SUBMISSION,
            target_type="WeeklyProgressReport",
            target_id=str(report.id),
            defaults={
                "subject": "Weekly report ready for review",
                "action_path": f"/projects/{project.id}/reports/{report.id}",
                "eligible_at": timezone.now(),
            },
        )
        artifact, _ = CodeArtifact.objects.get_or_create(
            project=project,
            name="Materials simulator",
            defaults={
                "description": "Shared team code library artifact",
                "tags": ["simulation"],
                "source_path_label": "team-code/materials-simulator",
                "created_by": student,
            },
        )
        CodeArtifactVersion.objects.get_or_create(
            artifact=artifact,
            project=project,
            version_label="v1",
            defaults={
                "commit_reference": "validation-ref-001",
                "description": "Initial validated local import",
                "filename": "materials-simulator.zip",
                "storage_key": "validation/code/materials-simulator.zip",
                "relative_path_manifest": ["src/model.py", "README.md"],
                "content_type": "application/zip",
                "size_bytes": 2048,
                "checksum_sha256": "e" * 64,
                "imported_by": student,
            },
        )
        call_command("remove_seeded_code_samples", verbosity=options["verbosity"])
        self.stdout.write(self.style.SUCCESS(f"Seeded validation project {project.id}"))
        self.stdout.write("")
        self.stdout.write(self.style.SUCCESS("Validation login credentials:"))
        for acct in VALIDATION_ACCOUNTS:
            self.stdout.write(
                f"  {acct['global_role']:10s} {acct['email']:30s} / {acct['password']}"
            )
