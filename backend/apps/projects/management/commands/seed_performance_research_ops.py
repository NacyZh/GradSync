from django.contrib.auth import get_user_model
from django.core.management.base import BaseCommand

from apps.library.models import PaperRecord
from apps.projects.models import ProjectMembership, ResearchProject
from apps.repositories.models import CodeArtifact, CodeArtifactVersion
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
            if index == 0:
                paper_existing = project.paper_records.count()
                for paper_index in range(paper_existing, 1000):
                    year = 2020 + (paper_index % 7)
                    PaperRecord.objects.create(
                        project=project,
                        title=f"Performance Paper {paper_index}",
                        authors=[f"Author {paper_index}"],
                        publication_year=year,
                        tags=["performance", f"tag-{paper_index % 10}"],
                        fingerprint=(
                            f"performance paper {paper_index}|author {paper_index}|{year}"
                        ),
                        created_by=advisor,
                    )
                artifact_existing = project.code_artifacts.count()
                for artifact_index in range(artifact_existing, 250):
                    artifact = CodeArtifact.objects.create(
                        project=project,
                        name=f"Performance Code {artifact_index}",
                        tags=["performance", f"tag-{artifact_index % 10}"],
                        created_by=advisor,
                    )
                    CodeArtifactVersion.objects.create(
                        artifact=artifact,
                        project=project,
                        version_label=f"v{artifact_index}",
                        filename=f"code-{artifact_index}.zip",
                        storage_key=f"performance/code-{artifact_index}.zip",
                        checksum_sha256=f"{artifact_index:064x}"[-64:],
                        imported_by=advisor,
                    )
        self.stdout.write(
            self.style.SUCCESS("Seeded 50 projects, 500 tasks, 1000 papers, and 250 code artifacts")
        )
