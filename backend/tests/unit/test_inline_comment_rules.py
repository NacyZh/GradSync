import pytest
from django.core.exceptions import ValidationError

from apps.projects.models import ProjectMembership, ResearchProject
from apps.submissions.comment_services import InlineCommentService
from apps.submissions.models import WeeklyProgressReport
from tests.factories.accounts import UserFactory


@pytest.mark.django_db
def test_comment_target_must_be_in_same_project():
    advisor = UserFactory(global_role="advisor")
    student = UserFactory(global_role="student")
    project_a = ResearchProject.objects.create(title="A", advisor=advisor)
    project_b = ResearchProject.objects.create(title="B", advisor=advisor)
    ProjectMembership.objects.create(project=project_a, user=advisor, role="advisor")
    report = WeeklyProgressReport.objects.create(
        project=project_b,
        student=student,
        report_week_start="2026-06-22",
        completed_work="Done",
        next_steps="Next",
    )

    with pytest.raises(ValidationError):
        InlineCommentService(advisor, project_a).create_comment(
            target_type="progress_report",
            target_id=report.id,
            anchor="p1",
            body="Nope",
        )
