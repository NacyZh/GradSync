import pytest

from apps.projects.models import ProjectMembership
from apps.submissions.report_analytics import calculate_report_analytics
from apps.submissions.report_period_services import open_reporting_period
from apps.submissions.report_services import submit_structured_report
from apps.submissions.report_template_services import ensure_default_report_template
from tests.factories.accounts import VerifiedUserFactory
from tests.factories.collaboration import ProjectMembershipFactory, ResearchProjectFactory


@pytest.mark.django_db
def test_analytics_reports_exact_counts_sources_and_missing_without_scores():
    advisor = VerifiedUserFactory(global_role="advisor", active_role="teacher")
    student = VerifiedUserFactory()
    project = ResearchProjectFactory(advisor=advisor)
    ProjectMembershipFactory(
        project=project, user=advisor, role=ProjectMembership.Role.ADVISOR
    )
    ProjectMembershipFactory(
        project=project, user=student, role=ProjectMembership.Role.STUDENT
    )
    template = ensure_default_report_template(actor=advisor, project=project)
    period = open_reporting_period(project=project, starts_on=template.created_at.date())
    report = submit_structured_report(
        actor=student,
        project=project,
        period=period,
        responses={
            "completed_work": "Done",
            "next_steps": "Continue",
            "progress_percent": 60,
        },
        idempotency_key="analytics-one",
    )
    result = calculate_report_analytics(
        actor=advisor,
        project=project,
        starts_on=period.starts_on,
        ends_on=period.ends_on,
    )
    assert result["submissionCounts"]["expected"] == 1
    assert result["submissionCounts"]["onTime"] == 1
    assert result["metricSeries"][0]["sourceReportIds"] == [report.id]
    assert "score" not in str(result).lower()
    assert "ranking" not in str(result).lower()
