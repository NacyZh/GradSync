from datetime import timedelta

import pytest
from django.core.exceptions import PermissionDenied
from django.utils import timezone

from apps.projects.execution_services import (
    create_deliverable,
    create_milestone,
    decide_deliverable,
    recommend_deliverable,
    submit_deliverable,
)
from apps.projects.models import Deliverable, Milestone, ProjectMembership
from tests.factories.accounts import VerifiedUserFactory
from tests.factories.collaboration import ProjectMembershipFactory, ResearchProjectFactory


@pytest.mark.django_db
def test_reviewer_recommendation_does_not_accept_deliverable():
    advisor = VerifiedUserFactory(global_role="advisor", active_role="teacher")
    reviewer = VerifiedUserFactory(global_role="advisor", active_role="teacher")
    student = VerifiedUserFactory(global_role="student", active_role="student")
    project = ResearchProjectFactory(advisor=advisor)
    for user, role in (
        (advisor, ProjectMembership.Role.ADVISOR),
        (reviewer, ProjectMembership.Role.REVIEWER),
        (student, ProjectMembership.Role.STUDENT),
    ):
        ProjectMembershipFactory(project=project, user=user, role=role)
    milestone = create_milestone(
        actor=advisor,
        project=project,
        title="Accepted result",
        description="",
        target_date=timezone.localdate() + timedelta(days=7),
        owner_ids=[student.id],
    )
    deliverable = create_deliverable(
        actor=advisor,
        milestone=milestone,
        title="Result",
        description="",
        acceptance_criteria="Evidence is reproducible.",
        due_date=timezone.localdate() + timedelta(days=5),
        assignee_ids=[student.id],
        reviewer_ids=[reviewer.id],
        reviewer_required=True,
    )
    revision = submit_deliverable(
        actor=student,
        deliverable=deliverable,
        description="Result package.",
        evidence=[{"external_url": "https://example.test/result", "label": "Result"}],
        idempotency_key="submission-1",
    )
    recommend_deliverable(
        actor=reviewer,
        revision=revision,
        recommendation="accept",
        rationale="Reproduction passed.",
    )
    deliverable.refresh_from_db()
    milestone.refresh_from_db()
    assert deliverable.current_status != Deliverable.Status.ACCEPTED
    assert milestone.current_status != Milestone.Status.COMPLETED

    with pytest.raises(PermissionDenied):
        decide_deliverable(
            actor=reviewer,
            revision=revision,
            decision="accepted",
            rationale="",
            idempotency_key="decision-reviewer",
        )

    decide_deliverable(
        actor=advisor,
        revision=revision,
        decision="accepted",
        rationale="",
        idempotency_key="decision-advisor",
    )
    deliverable.refresh_from_db()
    milestone.refresh_from_db()
    assert deliverable.current_status == Deliverable.Status.ACCEPTED
    assert milestone.current_status == Milestone.Status.COMPLETED
