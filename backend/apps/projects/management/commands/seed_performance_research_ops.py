from django.contrib.auth import get_user_model
from django.core.management.base import BaseCommand

from apps.projects.models import ProjectMembership, ResearchProject
from apps.tasks.models import Task


class Command(BaseCommand):
    help = "Seed projects and tasks for performance validation."

    def handle(self, *args, **options):
        user_model = get_user_model()
        advisor, _ = user_model.objects.get_or_create(
            email="perf-advisor@example.com",
            defaults={"name": "Performance Advisor", "global_role": "advisor"},
        )
        for index in range(50):
            project, _ = ResearchProject.objects.get_or_create(
                title=f"Performance Project {index}", advisor=advisor
            )
            ProjectMembership.objects.get_or_create(project=project, user=advisor, role="advisor")
            existing = project.tasks.count()
            for task_index in range(existing, 10):
                Task.objects.create(project=project, title=f"Task {task_index}", created_by=advisor)
        self.stdout.write(self.style.SUCCESS("Seeded 50 projects with 500 total tasks"))
