import pytest

from apps.projects.models import ProjectMembership
from apps.submissions.report_period_services import open_reporting_period
from apps.submissions.report_services import submit_structured_report
from apps.submissions.report_template_services import ensure_default_report_template
from tests.factories.accounts import VerifiedUserFactory
from tests.factories.collaboration import ProjectMembershipFactory, ResearchProjectFactory


@pytest.mark.django_db
def test_structured_response_validates_required_and_numeric_values():
    advisor = VerifiedUserFactory(global_role="advisor", active_role="teacher")
    student = VerifiedUserFactory(global_role="student", active_role="student")
    project = ResearchProjectFactory(advisor=advisor)
    ProjectMembershipFactory(
        project=project, user=advisor, role=ProjectMembership.Role.ADVISOR
    )
    ProjectMembershipFactory(
        project=project, user=student, role=ProjectMembership.Role.STUDENT
    )
    template = ensure_default_report_template(actor=advisor, project=project)
    period = open_reporting_period(project=project, starts_on=template.created_at.date())
    fields = {field.key: field for field in period.template_version.fields.all()}
    with pytest.raises(ValueError, match="required"):
        submit_structured_report(
            actor=student,
            project=project,
            period=period,
            responses={},
            idempotency_key="missing-fields",
        )
    report = submit_structured_report(
        actor=student,
        project=project,
        period=period,
        responses={
            "completed_work": "Validated experiment.",
            "next_steps": "Run the next batch.",
            "progress_percent": 55,
        },
        idempotency_key="structured-one",
    )
    assert report.responses.get(
        template_field=fields["progress_percent"]
    ).numeric_value == 55
