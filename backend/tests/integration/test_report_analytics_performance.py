from datetime import timedelta

import pytest
from django.core.exceptions import ValidationError
from django.utils import timezone

from apps.projects.models import ProjectMembership
from apps.submissions.report_analytics import calculate_report_analytics
from tests.factories.accounts import VerifiedUserFactory
from tests.factories.collaboration import ProjectMembershipFactory, ResearchProjectFactory


@pytest.mark.django_db
def test_analytics_range_is_bounded_and_contains_no_rank_or_score():
    advisor = VerifiedUserFactory(global_role="advisor", active_role="teacher")
    project = ResearchProjectFactory(advisor=advisor)
    ProjectMembershipFactory(project=project, user=advisor, role=ProjectMembership.Role.ADVISOR)
    today = timezone.localdate()
    result = calculate_report_analytics(
        actor=advisor,
        project=project,
        starts_on=today - timedelta(days=7),
        ends_on=today,
    )
    serialized = str(result).lower()
    assert "rank" not in serialized
    assert "score" not in serialized
    with pytest.raises(ValidationError):
        calculate_report_analytics(
            actor=advisor,
            project=project,
            starts_on=today - timedelta(weeks=105),
            ends_on=today,
        )
