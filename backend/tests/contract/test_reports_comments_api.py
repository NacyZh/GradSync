import pytest

from apps.projects.models import ProjectMembership, ResearchProject
from apps.submissions.models import Draft, DraftVersion, WeeklyProgressReport
from tests.factories.accounts import UserFactory
from tests.helpers import authenticate


@pytest.mark.django_db
def test_student_can_submit_weekly_report(api_client):
    student = UserFactory(global_role="student")
    advisor = UserFactory(global_role="advisor")
    project = ResearchProject.objects.create(title="Project", advisor=advisor)
    ProjectMembership.objects.create(project=project, user=student, role="student")

    response = authenticate(api_client, student).post(
        f"/api/projects/{project.id}/reports/",
        {
            "report_week_start": "2026-06-22",
            "completed_work": "Read papers",
            "next_steps": "Draft intro",
        },
        format="json",
    )

    assert response.status_code == 201


@pytest.mark.django_db
def test_advisor_can_comment_on_draft_version(api_client):
    advisor = UserFactory(global_role="advisor")
    student = UserFactory(global_role="student")
    project = ResearchProject.objects.create(title="Project", advisor=advisor)
    ProjectMembership.objects.create(project=project, user=advisor, role="advisor")
    draft = Draft.objects.create(project=project, student=student, title="Paper")
    version = DraftVersion.objects.create(
        project=project,
        draft=draft,
        submitted_by=student,
        version_number=1,
        content_reference="paper-v1",
    )

    response = authenticate(api_client, advisor).post(
        f"/api/projects/{project.id}/comments/",
        {
            "target_type": "draft_version",
            "target_id": version.id,
            "anchor": "p1",
            "body": "Clarify claim",
        },
        format="json",
    )

    assert response.status_code == 201


@pytest.mark.django_db
def test_duplicate_weekly_report_is_rejected(api_client):
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

    response = authenticate(api_client, student).post(
        f"/api/projects/{project.id}/reports/",
        {"report_week_start": "2026-06-22", "completed_work": "Again", "next_steps": "Again"},
        format="json",
    )

    assert response.status_code == 400
