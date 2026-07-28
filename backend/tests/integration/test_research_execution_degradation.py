from datetime import timedelta

import pytest
from django.utils import timezone

from apps.projects.models import ProjectMembership
from apps.submissions.report_analytics import calculate_report_analytics
from tests.factories.accounts import VerifiedUserFactory
from tests.factories.collaboration import ProjectMembershipFactory, ResearchProjectFactory


@pytest.mark.django_db
def test_source_analytics_remain_available_without_cache(monkeypatch):
    advisor = VerifiedUserFactory(global_role="advisor", active_role="teacher")
    project = ResearchProjectFactory(advisor=advisor)
    ProjectMembershipFactory(project=project, user=advisor, role=ProjectMembership.Role.ADVISOR)
    monkeypatch.setenv("REDIS_URL", "redis://unavailable.invalid/0")
    today = timezone.localdate()
    result = calculate_report_analytics(
        actor=advisor,
        project=project,
        starts_on=today - timedelta(days=7),
        ends_on=today,
    )
    assert result["submissionCounts"]["expected"] == 0
