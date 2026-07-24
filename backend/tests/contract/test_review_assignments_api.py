import pytest

from apps.submissions.models import WeeklyProgressReport
from tests.factories.accounts import VerifiedUserFactory
from tests.factories.collaboration import ProjectMembershipFactory, ResearchProjectFactory


@pytest.mark.django_db
def test_primary_advisor_assigns_reviewer_to_one_report(api_client):
    owner = VerifiedUserFactory(global_role="advisor", active_role="teacher")
    reviewer = VerifiedUserFactory(global_role="advisor", active_role="teacher")
    student = VerifiedUserFactory(global_role="student", active_role="student")
    project = ResearchProjectFactory(advisor=owner)
    ProjectMembershipFactory(project=project, user=owner, role="advisor")
    membership = ProjectMembershipFactory(project=project, user=reviewer, role="reviewer")
    report = WeeklyProgressReport.objects.create(
        project=project,
        student=student,
        report_week_start="2026-07-20",
        completed_work="Done",
        next_steps="Continue",
    )
    api_client.force_authenticate(owner)

    response = api_client.post(
        f"/api/projects/{project.id}/review-assignments/",
        {"reviewerMembershipId": membership.id, "weeklyReportId": report.id},
        format="json",
    )
    assert response.status_code == 201
    assert response.json()["weeklyReportId"] == report.id
