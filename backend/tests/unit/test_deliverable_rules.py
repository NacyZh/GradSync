from datetime import timedelta

import pytest
from django.utils import timezone

from apps.projects.execution_services import (
    create_deliverable,
    create_milestone,
    submit_deliverable,
)
from apps.projects.models import DeliverableEvidence, ProjectMembership
from tests.factories.accounts import VerifiedUserFactory
from tests.factories.collaboration import ProjectMembershipFactory, ResearchProjectFactory


@pytest.mark.django_db
def test_submission_requires_evidence_and_rejects_unsafe_url():
    advisor = VerifiedUserFactory(global_role="advisor", active_role="teacher")
    student = VerifiedUserFactory(global_role="student", active_role="student")
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
        title="Evidence",
        description="",
        target_date=timezone.localdate() + timedelta(days=7),
        owner_ids=[student.id],
    )
    deliverable = create_deliverable(
        actor=advisor,
        milestone=milestone,
        title="Dataset",
        description="",
        acceptance_criteria="Dataset and provenance are available.",
        due_date=timezone.localdate() + timedelta(days=5),
        assignee_ids=[student.id],
    )

    with pytest.raises(ValueError, match="evidence"):
        submit_deliverable(
            actor=student,
            deliverable=deliverable,
            description="Dataset snapshot.",
            evidence=[],
            idempotency_key="empty",
        )
    with pytest.raises(ValueError, match="HTTPS"):
        submit_deliverable(
            actor=student,
            deliverable=deliverable,
            description="Dataset snapshot.",
            evidence=[{"external_url": "http://example.test/data", "label": "Data"}],
            idempotency_key="unsafe",
        )

    revision = submit_deliverable(
        actor=student,
        deliverable=deliverable,
        description="Dataset snapshot.",
        evidence=[{"external_url": "https://example.test/data", "label": "Data"}],
        idempotency_key="valid",
    )
    assert revision.evidence.get().source_type_snapshot == DeliverableEvidence.SourceType.URL
    deliverable.refresh_from_db()
    assert deliverable.current_revision_id == revision.id
