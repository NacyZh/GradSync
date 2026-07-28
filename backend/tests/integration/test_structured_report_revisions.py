import pytest

from apps.projects.models import ProjectMembership
from apps.submissions.report_period_services import open_reporting_period
from apps.submissions.report_services import submit_structured_report
from apps.submissions.report_template_services import ensure_default_report_template
from tests.factories.accounts import VerifiedUserFactory
from tests.factories.collaboration import ProjectMembershipFactory, ResearchProjectFactory


@pytest.mark.django_db
def test_returned_structured_report_resubmits_against_locked_version():
    advisor = VerifiedUserFactory(global_role="advisor", active_role="teacher")
    student = VerifiedUserFactory(global_role="student", active_role="student")
    project = ResearchProjectFactory(advisor=advisor)
    ProjectMembershipFactory(project=project, user=advisor, role=ProjectMembership.Role.ADVISOR)
    ProjectMembershipFactory(project=project, user=student, role=ProjectMembership.Role.STUDENT)
    template = ensure_default_report_template(actor=advisor, project=project)
    period = open_reporting_period(project=project, starts_on=template.created_at.date())
    first = submit_structured_report(
        actor=student,
        project=project,
        period=period,
        responses={
            "completed_work": "First result.",
            "next_steps": "Validate.",
            "progress_percent": 40,
        },
        idempotency_key="revision-one",
    )
    first.review_status = first.ReviewStatus.NEEDS_REVISION
    first.save(update_fields=["review_status"])
    second = submit_structured_report(
        actor=student,
        project=project,
        period=period,
        responses={
            "completed_work": "Corrected result.",
            "next_steps": "Publish.",
            "progress_percent": 60,
        },
        idempotency_key="revision-two",
    )
    assert second.revision_number == 2
    assert second.template_version_id == first.template_version_id
    assert first.responses.get(template_field__key="completed_work").value == "First result."
