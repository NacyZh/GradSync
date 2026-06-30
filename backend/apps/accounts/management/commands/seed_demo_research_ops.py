from django.contrib.auth import get_user_model
from django.core.management.base import BaseCommand
from django.utils import timezone

from apps.notifications.models import Notification
from apps.projects.models import ProjectMembership, ResearchProject
from apps.resources.models import Booking, LabResource
from apps.submissions.models import Draft, DraftVersion, InlineComment, WeeklyProgressReport
from apps.tasks.models import Task

DEMO_ACCOUNTS = [
    {
        "email": "admin@gradsync.local",
        "name": "Admin Demo",
        "global_role": "admin",
        "password": "admin123",
    },
    {
        "email": "advisor@example.com",
        "name": "Advisor Demo",
        "global_role": "advisor",
        "password": "advisor123",
    },
    {
        "email": "student@example.com",
        "name": "Student Demo",
        "global_role": "student",
        "password": "student123",
    },
    {
        "email": "reviewer@example.com",
        "name": "Reviewer Demo",
        "global_role": "advisor",
        "password": "reviewer123",
    },
]


class Command(BaseCommand):
    help = "Seed demo advisor and student accounts for research operations validation."

    def handle(self, *args, **options):
        user_model = get_user_model()

        created_users = {}
        for acct in DEMO_ACCOUNTS:
            user, created = user_model.objects.get_or_create(
                email=acct["email"],
                defaults={
                    "name": acct["name"],
                    "global_role": acct["global_role"],
                    "status": user_model.Status.ACTIVE,
                },
            )
            user.set_password(acct["password"])
            user.save(update_fields=["password"])
            created_users[acct["email"]] = user
            verb = "Created" if created else "Updated"
            self.stdout.write(
                f"  {verb} {acct['global_role']}: {acct['email']} / {acct['password']}"
            )

        advisor = created_users["advisor@example.com"]
        student = created_users["student@example.com"]
        reviewer = created_users["reviewer@example.com"]
        project, _ = ResearchProject.objects.get_or_create(
            title="Demo Research Project",
            defaults={
                "description": "Quickstart validation project",
                "advisor": advisor,
                "starts_on": timezone.localdate(),
                "ends_on": timezone.localdate() + timezone.timedelta(days=7),
            },
        )
        for user, role in [(advisor, "advisor"), (student, "student"), (reviewer, "reviewer")]:
            ProjectMembership.objects.update_or_create(
                project=project, user=user, defaults={"role": role, "status": "active"}
            )
        parent, _ = Task.objects.get_or_create(
            project=project,
            title="Write thesis chapter",
            defaults={
                "created_by": advisor,
                "assignee": student,
                "deadline_at": timezone.now() + timezone.timedelta(days=7),
            },
        )
        child, _ = Task.objects.get_or_create(
            project=project,
            title="Prepare related work",
            defaults={
                "created_by": advisor,
                "assignee": student,
                "parent_task": parent,
                "deadline_at": timezone.now() + timezone.timedelta(days=1),
            },
        )
        resource, _ = LabResource.objects.get_or_create(
            name="Demo lab seat", defaults={"resource_type": "seat", "location": "Room 101"}
        )
        Booking.objects.get_or_create(
            project=project,
            resource=resource,
            requested_by=student,
            starts_at=timezone.now() + timezone.timedelta(days=1),
            ends_at=timezone.now() + timezone.timedelta(days=1, hours=1),
            defaults={"purpose": "Quickstart booking"},
        )
        draft, _ = Draft.objects.get_or_create(project=project, student=student, title="Demo paper")
        version, _ = DraftVersion.objects.get_or_create(
            draft=draft,
            project=project,
            version_number=1,
            defaults={"submitted_by": student, "content_reference": "demo-paper-v1"},
        )
        report, _ = WeeklyProgressReport.objects.get_or_create(
            project=project,
            student=student,
            report_week_start=timezone.localdate(),
            defaults={
                "completed_work": "Completed experiment setup",
                "blockers": "",
                "next_steps": "Analyze results",
            },
        )
        InlineComment.objects.get_or_create(
            project=project,
            target_type="draft_version",
            target_id=version.id,
            author=advisor,
            anchor="abstract",
            defaults={"body": "Clarify contribution"},
        )
        Notification.objects.get_or_create(
            project=project,
            recipient=advisor,
            sender=student,
            event_type=Notification.EventType.NEW_SUBMISSION,
            target_type="WeeklyProgressReport",
            target_id=str(report.id),
            defaults={
                "subject": "Demo report ready for review",
                "action_path": f"/projects/{project.id}/reports/{report.id}",
                "eligible_at": timezone.now(),
            },
        )
        self.stdout.write(self.style.SUCCESS(f"Seeded quickstart project {project.id}"))
        self.stdout.write("")
        self.stdout.write(self.style.SUCCESS("Demo login credentials:"))
        for acct in DEMO_ACCOUNTS:
            self.stdout.write(
                f"  {acct['global_role']:10s} {acct['email']:30s} / {acct['password']}"
            )
