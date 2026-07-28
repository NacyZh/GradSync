from datetime import timedelta

import pytest
from django.utils import timezone

from apps.projects.execution_services import (
    create_deliverable,
    create_milestone,
    submit_deliverable,
)
from apps.projects.models import ProjectMembership
from tests.factories.accounts import VerifiedUserFactory
from tests.factories.collaboration import ProjectMembershipFactory, ResearchProjectFactory


@pytest.mark.django_db
def test_submission_idempotency_returns_one_revision():
    advisor = VerifiedUserFactory(global_role="advisor", active_role="teacher")
    student = VerifiedUserFactory()
    project = ResearchProjectFactory(advisor=advisor)
    ProjectMembershipFactory(
        project=project, user=advisor, role=ProjectMembership.Role.ADVISOR
    )
    ProjectMembershipFactory(
        project=project, user=student, role=ProjectMembership.Role.STUDENT
    )
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
        acceptance_criteria="Complete.",
        due_date=timezone.localdate() + timedelta(days=5),
        assignee_ids=[student.id],
    )
    payload = {
        "actor": student,
        "deliverable": deliverable,
        "description": "Retry-safe",
        "evidence": [{"external_url": "https://example.test/v1", "label": "v1"}],
        "idempotency_key": "same-request",
    }
    assert submit_deliverable(**payload).id == submit_deliverable(**payload).id
    assert deliverable.revisions.count() == 1
