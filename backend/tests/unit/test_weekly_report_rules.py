import pytest
from apps.projects.models import ProjectMembership, ResearchProject
from apps.submissions.models import WeeklyProgressReport
from tests.factories.accounts import UserFactory


@pytest.mark.django_db
def test_report_revisions_are_unique_per_project_student_week():
    student = UserFactory(global_role="student")
    advisor = UserFactory(global_role="advisor")
    project = ResearchProject.objects.create(title="Project", advisor=advisor)
    ProjectMembership.objects.create(project=project, user=student, role="student")
    WeeklyProgressReport.objects.create(
        project=project,
        student=student,
        report_week_start="2026-06-22",
        completed_work="Done",
        next_steps="Next",
    )

    second = WeeklyProgressReport.objects.create(
        project=project,
        student=student,
        report_week_start="2026-06-22",
        revision_number=2,
        completed_work="Again",
        next_steps="Again",
    )

    assert second.revision_number == 2
