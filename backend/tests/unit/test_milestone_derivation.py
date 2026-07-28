from datetime import timedelta

import pytest
from django.utils import timezone

from apps.projects.execution_services import create_deliverable, create_milestone
from apps.projects.models import Deliverable, Milestone, ProjectMembership
from tests.factories.accounts import VerifiedUserFactory
from tests.factories.collaboration import ProjectMembershipFactory, ResearchProjectFactory


@pytest.mark.django_db
def test_milestone_status_is_derived_from_required_deliverables():
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
        title="Validated prototype",
        description="A reproducible implementation.",
        target_date=timezone.localdate() + timedelta(days=7),
        owner_ids=[student.id],
    )
    deliverable = create_deliverable(
        actor=advisor,
        milestone=milestone,
        title="Prototype package",
        description="Package and execution notes.",
        acceptance_criteria="Runs from a clean environment.",
        due_date=timezone.localdate() + timedelta(days=5),
        assignee_ids=[student.id],
    )

    assert milestone.current_status == Milestone.Status.PLANNED
    deliverable.current_status = Deliverable.Status.BLOCKED
    deliverable.blocker_summary = "Awaiting instrument access."
    deliverable.save(update_fields=["current_status", "blocker_summary", "updated_at"])
    milestone.reconcile_status()
    milestone.refresh_from_db()
    assert milestone.current_status == Milestone.Status.BLOCKED


@pytest.mark.django_db
def test_milestone_rejects_inactive_owner():
    advisor = VerifiedUserFactory(global_role="advisor", active_role="teacher")
    removed = VerifiedUserFactory()
    project = ResearchProjectFactory(advisor=advisor)
    ProjectMembershipFactory(
        project=project, user=advisor, role=ProjectMembership.Role.ADVISOR
    )
    ProjectMembershipFactory(
        project=project,
        user=removed,
        role=ProjectMembership.Role.STUDENT,
        status=ProjectMembership.Status.REMOVED,
    )

    with pytest.raises(ValueError, match="active project member"):
        create_milestone(
            actor=advisor,
            project=project,
            title="Invalid milestone",
            description="",
            target_date=timezone.localdate(),
            owner_ids=[removed.id],
        )
