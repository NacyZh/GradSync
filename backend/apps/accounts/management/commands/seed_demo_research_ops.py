from django.contrib.auth import get_user_model
from django.core.management.base import BaseCommand
from django.utils import timezone

from apps.notifications.models import Notification
from apps.projects.models import ProjectMembership, ResearchProject
from apps.resources.models import Booking, LabResource
from apps.submissions.models import Draft, DraftVersion, InlineComment, WeeklyProgressReport
from apps.tasks.models import Task


class Command(BaseCommand):
    help = "Seed demo advisor and student accounts for research operations validation."

    def handle(self, *args, **options):
        user_model = get_user_model()
        advisor, _ = user_model.objects.get_or_create(
            email="advisor@example.com",
            defaults={"name": "Advisor Demo", "global_role": "advisor"},
        )
        student, _ = user_model.objects.get_or_create(
            email="student@example.com",
            defaults={"name": "Student Demo", "global_role": "student"},
        )
        reviewer, _ = user_model.objects.get_or_create(
            email="reviewer@example.com",
            defaults={"name": "Reviewer Demo", "global_role": "advisor"},
        )
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
        self.stdout.write(
            self.style.SUCCESS(
                f"Seeded quickstart project {project.id} with {advisor.email} and {student.email}"
            )
        )
