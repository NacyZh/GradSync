from django.contrib.auth import get_user_model
from django.core.management import call_command
from django.core.management.base import BaseCommand
from django.utils import timezone

from apps.notifications.models import Notification
from apps.projects.models import ProjectMembership, ResearchProject
from apps.resources.models import Booking, LabResource
from apps.submissions.models import Draft, DraftVersion, InlineComment, WeeklyProgressReport
from apps.tasks.models import Task


class Command(BaseCommand):
    help = "Reset and seed deterministic data for full-stack Playwright tests."

    def handle(self, *args, **options):
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

        draft = Draft.objects.create(project=project, student=student, title="Paper A")
        DraftVersion.objects.create(
            project=project,
            draft=draft,
            version_number=1,
            submitted_by=student,
            content_reference="paper-v1.pdf",
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

        resource = LabResource.objects.create(
            name="Confocal microscope",
            resource_type="equipment",
            location="Room 2",
        )
        LabResource.objects.create(name="Open bench", resource_type="seat", location="Room 3")
        Booking.objects.create(
            project=project,
            resource=resource,
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

        self.stdout.write(
            self.style.SUCCESS(
                "Seeded full-stack e2e users: admin@gradsync.local, "
                "advisor@example.edu, student@example.edu / password123"
            )
        )
