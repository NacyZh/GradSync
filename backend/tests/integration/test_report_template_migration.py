import pytest
from django.utils import timezone

from apps.projects.models import ProjectMembership
from apps.submissions.models import WeeklyProgressReport
from apps.submissions.report_period_services import open_reporting_period
from apps.submissions.report_template_services import ensure_default_report_template
from tests.factories.accounts import VerifiedUserFactory
from tests.factories.collaboration import ProjectMembershipFactory, ResearchProjectFactory


@pytest.mark.django_db
def test_legacy_report_remains_queryable_while_default_template_is_added():
    advisor = VerifiedUserFactory(global_role="advisor", active_role="teacher")
    student = VerifiedUserFactory(global_role="student", active_role="student")
    project = ResearchProjectFactory(advisor=advisor)
    ProjectMembershipFactory(project=project, user=advisor, role=ProjectMembership.Role.ADVISOR)
    ProjectMembershipFactory(project=project, user=student, role=ProjectMembership.Role.STUDENT)
    legacy = WeeklyProgressReport.objects.create(
        project=project,
        student=student,
        report_week_start=timezone.localdate(),
        completed_work="Historical work",
        blockers="Historical blocker",
        next_steps="Historical next step",
        review_status=WeeklyProgressReport.ReviewStatus.REVIEWED,
    )
    template = ensure_default_report_template(actor=advisor, project=project)
    period = open_reporting_period(project=project, starts_on=legacy.report_week_start)
    legacy.refresh_from_db()
    assert legacy.completed_work == "Historical work"
    assert legacy.review_status == WeeklyProgressReport.ReviewStatus.REVIEWED
    assert period.template_version_id == template.id
