import pytest
from rest_framework.test import APIClient

from apps.projects.models import ProjectMembership
from apps.submissions.report_period_services import open_reporting_period
from apps.submissions.report_template_services import ensure_default_report_template
from tests.factories.accounts import VerifiedUserFactory
from tests.factories.collaboration import ProjectMembershipFactory, ResearchProjectFactory


@pytest.mark.django_db
def test_template_period_submission_analytics_and_export_contract():
    advisor = VerifiedUserFactory(global_role="advisor", active_role="teacher")
    student = VerifiedUserFactory(global_role="student", active_role="student")
    project = ResearchProjectFactory(advisor=advisor)
    ProjectMembershipFactory(project=project, user=advisor, role=ProjectMembership.Role.ADVISOR)
    ProjectMembershipFactory(project=project, user=student, role=ProjectMembership.Role.STUDENT)
    template = ensure_default_report_template(actor=advisor, project=project)
    period = open_reporting_period(project=project, starts_on=template.created_at.date())
    client = APIClient()
    client.force_authenticate(advisor)
    templates = client.get(f"/api/projects/{project.id}/report-templates/")
    assert templates.status_code == 200
    assert templates.data["capabilities"]["canEditTemplate"] is True
    assert client.get(f"/api/projects/{project.id}/reporting-periods/").status_code == 200

    client.force_authenticate(student)
    fields = {field.key: field for field in template.fields.all()}
    submitted = client.post(
        f"/api/projects/{project.id}/reports/",
        {
            "reportingPeriodId": period.id,
            "responses": [
                {"fieldId": fields["completed_work"].id, "value": "Pilot complete."},
                {"fieldId": fields["next_steps"].id, "value": "Analyze results."},
                {"fieldId": fields["progress_percent"].id, "value": 60},
            ],
            "idempotencyKey": "structured-api-001",
        },
        format="json",
    )
    assert submitted.status_code == 201
    assert submitted.data["templateVersionId"] == template.id

    client.force_authenticate(advisor)
    query = f"from={period.starts_on}&to={period.ends_on}"
    analytics = client.get(f"/api/projects/{project.id}/report-analytics/?{query}")
    assert analytics.status_code == 200
    assert analytics.data["submissionCounts"]["expected"] == 1
    exported = client.get(f"/api/projects/{project.id}/report-analytics/export/?{query}")
    assert exported.status_code == 200
    assert exported["Content-Type"].startswith("text/csv")
