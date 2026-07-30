import importlib

import pytest
from django.apps import apps
from django.utils import timezone

from apps.accounts.models import TeacherProfile
from apps.projects.models import ProjectMembership, ResearchProject
from tests.factories.accounts import VerifiedUserFactory
from tests.factories.collaboration import ProjectMembershipFactory, ResearchProjectFactory


@pytest.mark.django_db
def test_governance_schema_preserves_student_memberships_and_hold_reason():
    administrator = VerifiedUserFactory(global_role="admin", active_role="administrator")
    student = VerifiedUserFactory(global_role="student", active_role="student")
    project = ResearchProjectFactory(
        advisor=administrator,
        governance_state=ResearchProject.GovernanceState.HOLD,
        governance_hold_reason=ResearchProject.GovernanceHoldReason.LEGACY_ADMIN_OWNER,
    )
    membership = ProjectMembershipFactory(
        project=project,
        user=student,
        role=ProjectMembership.Role.STUDENT,
    )

    membership.refresh_from_db()
    project.refresh_from_db()
    assert membership.status == ProjectMembership.Status.ACTIVE
    assert project.governance_state == ResearchProject.GovernanceState.HOLD
    assert project.governance_hold_reason == "legacy_admin_owner"


@pytest.mark.django_db
def test_legacy_advisor_defaults_are_repaired_without_losing_project_access():
    advisor = VerifiedUserFactory(
        global_role="advisor",
        requested_role="student",
        active_role="student",
        email_verified_at=None,
    )
    project = ResearchProjectFactory(
        advisor=advisor,
        governance_state=ResearchProject.GovernanceState.HOLD,
        governance_hold_reason=ResearchProject.GovernanceHoldReason.OWNER_INELIGIBLE,
        governance_hold_started_at=timezone.now(),
    )
    membership = ProjectMembershipFactory(
        project=project,
        user=advisor,
        role=ProjectMembership.Role.ADVISOR,
        status=ProjectMembership.Status.REMOVED,
        removed_at=timezone.now(),
    )
    migration = importlib.import_module(
        "apps.projects.migrations.0007_repair_legacy_project_owners"
    )

    migration.repair_legacy_project_owners(apps, None)
    migration.repair_legacy_project_owners(apps, None)

    advisor.refresh_from_db()
    membership.refresh_from_db()
    project.refresh_from_db()
    assert advisor.requested_role == "teacher"
    assert advisor.active_role == "teacher"
    assert advisor.email_verified_at is not None
    assert TeacherProfile.objects.filter(user=advisor).exists()
    assert membership.role == ProjectMembership.Role.ADVISOR
    assert membership.status == ProjectMembership.Status.ACTIVE
    assert membership.removed_at is None
    assert project.governance_state == ResearchProject.GovernanceState.NORMAL
    assert project.governance_hold_reason == ""
    assert project.memberships.filter(role="advisor", status="active").count() == 1


@pytest.mark.django_db
def test_legacy_owner_repair_does_not_unfreeze_ineligible_or_conflicting_projects():
    suspended = VerifiedUserFactory(
        global_role="advisor",
        status="suspended",
        active_role="student",
        email_verified_at=None,
    )
    suspended_project = ResearchProjectFactory(
        advisor=suspended,
        governance_state=ResearchProject.GovernanceState.HOLD,
        governance_hold_reason=ResearchProject.GovernanceHoldReason.OWNER_INELIGIBLE,
    )
    ProjectMembershipFactory(
        project=suspended_project,
        user=suspended,
        role=ProjectMembership.Role.ADVISOR,
        status=ProjectMembership.Status.REMOVED,
    )
    legacy_owner = VerifiedUserFactory(
        global_role="advisor",
        active_role="student",
        email_verified_at=None,
    )
    replacement = VerifiedUserFactory(global_role="advisor", active_role="teacher")
    conflicting_project = ResearchProjectFactory(
        advisor=legacy_owner,
        governance_state=ResearchProject.GovernanceState.HOLD,
        governance_hold_reason=ResearchProject.GovernanceHoldReason.OWNER_INELIGIBLE,
    )
    ProjectMembershipFactory(
        project=conflicting_project,
        user=legacy_owner,
        role=ProjectMembership.Role.ADVISOR,
        status=ProjectMembership.Status.REMOVED,
    )
    ProjectMembershipFactory(
        project=conflicting_project,
        user=replacement,
        role=ProjectMembership.Role.ADVISOR,
    )
    migration = importlib.import_module(
        "apps.projects.migrations.0007_repair_legacy_project_owners"
    )

    migration.repair_legacy_project_owners(apps, None)

    suspended_project.refresh_from_db()
    conflicting_project.refresh_from_db()
    assert suspended_project.governance_state == ResearchProject.GovernanceState.HOLD
    assert conflicting_project.governance_state == ResearchProject.GovernanceState.HOLD
