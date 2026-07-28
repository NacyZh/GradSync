from time import perf_counter

import pytest
from django.utils import timezone

from apps.projects.models import ProjectMembership, RiskRecord
from apps.submissions.report_analytics import calculate_report_analytics
from tests.factories.accounts import VerifiedUserFactory
from tests.factories.collaboration import ProjectMembershipFactory, ResearchProjectFactory


@pytest.mark.django_db
def test_bounded_governance_and_analytics_reads_complete_under_three_seconds():
    advisor = VerifiedUserFactory(global_role="advisor", active_role="teacher")
    project = ResearchProjectFactory(advisor=advisor)
    ProjectMembershipFactory(project=project, user=advisor, role=ProjectMembership.Role.ADVISOR)
    RiskRecord.objects.bulk_create(
        [
            RiskRecord(
                project=project,
                title=f"Risk {index}",
                description="Bounded fixture",
                raised_by=advisor,
            )
            for index in range(500)
        ]
    )
    started = perf_counter()
    assert list(project.risks.order_by("id")[:100])
    today = timezone.localdate()
    calculate_report_analytics(actor=advisor, project=project, starts_on=today, ends_on=today)
    assert perf_counter() - started < 3
