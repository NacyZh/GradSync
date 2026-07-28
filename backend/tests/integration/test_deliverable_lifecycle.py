from datetime import timedelta

import pytest
from django.utils import timezone

from apps.projects.execution_services import (
    create_deliverable,
    create_milestone,
    decide_deliverable,
    submit_deliverable,
)
from apps.projects.models import Deliverable, ProjectMembership
from tests.factories.accounts import VerifiedUserFactory
from tests.factories.collaboration import ProjectMembershipFactory, ResearchProjectFactory


@pytest.mark.django_db
def test_submit_return_resubmit_accept_preserves_revisions():
    advisor = VerifiedUserFactory(global_role="advisor", active_role="teacher")
    student = VerifiedUserFactory(global_role="student", active_role="student")
    project = ResearchProjectFactory(advisor=advisor)
    for user, role in (
        (advisor, ProjectMembership.Role.ADVISOR),
        (student, ProjectMembership.Role.STUDENT),
    ):
        ProjectMembershipFactory(project=project, user=user, role=role)
    milestone = create_milestone(
        actor=advisor,
        project=project,
        title="Outcome",
        description="",
        target_date=timezone.localdate() + timedelta(days=7),
        owner_ids=[student.id],
    )
    deliverable = create_deliverable(
        actor=advisor,
        milestone=milestone,
        title="Package",
        description="",
        acceptance_criteria="Runs cleanly.",
        due_date=timezone.localdate() + timedelta(days=5),
        assignee_ids=[student.id],
    )
    first = submit_deliverable(
        actor=student,
        deliverable=deliverable,
        description="First",
        evidence=[{"external_url": "https://example.test/v1", "label": "v1"}],
        idempotency_key="revision-one",
    )
    decide_deliverable(
        actor=advisor,
        revision=first,
        decision="returned",
        rationale="Add provenance.",
        idempotency_key="return-one",
    )
    second = submit_deliverable(
        actor=student,
        deliverable=deliverable,
        description="Second",
        evidence=[{"external_url": "https://example.test/v2", "label": "v2"}],
        idempotency_key="revision-two",
    )
    decide_deliverable(
        actor=advisor,
        revision=second,
        decision="accepted",
        rationale="",
        idempotency_key="accept-two",
    )
    deliverable.refresh_from_db()
    first.refresh_from_db()
    assert first.description_snapshot == "First"
    assert deliverable.current_status == Deliverable.Status.ACCEPTED
    assert deliverable.accepted_revision_id == second.id
