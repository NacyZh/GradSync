import importlib

import pytest
from django.apps import apps
from rest_framework.test import APIClient

from apps.accounts.models import TeacherProfile
from apps.projects.models import ProjectMembership
from tests.factories.accounts import VerifiedUserFactory
from tests.factories.collaboration import ProjectMembershipFactory, ResearchProjectFactory


@pytest.mark.django_db
def test_legacy_student_project_execution_access_is_restored():
    student = VerifiedUserFactory(
        global_role="student",
        requested_role="student",
        active_role="student",
        status="active",
        email_verified_at=None,
    )
    project = ResearchProjectFactory()
    ProjectMembershipFactory(
        project=project,
        user=student,
        role=ProjectMembership.Role.STUDENT,
    )
    client = APIClient()
    client.force_authenticate(student)

    listed = client.get("/api/projects/")
    forbidden = client.get(f"/api/projects/{project.id}/execution-summary/")
    assert listed.status_code == 200
    assert forbidden.status_code == 403

    migration = importlib.import_module(
        "apps.accounts.migrations.0008_repair_legacy_active_accounts"
    )
    migration.repair_legacy_active_accounts(apps, None)
    student.refresh_from_db()

    restored = client.get(f"/api/projects/{project.id}/execution-summary/")
    assert student.email_verified_at is not None
    assert restored.status_code == 200
    assert restored.data["capabilities"]["canSubmitAssignedDeliverables"] is True


@pytest.mark.django_db
def test_legacy_active_roles_are_mapped_without_activating_pending_accounts():
    advisor = VerifiedUserFactory(
        global_role="advisor",
        requested_role="student",
        active_role="student",
        status="active",
        email_verified_at=None,
    )
    administrator = VerifiedUserFactory(
        global_role="admin",
        requested_role="student",
        active_role="student",
        status="active",
        email_verified_at=None,
    )
    pending = VerifiedUserFactory(
        global_role="student",
        status="pending_email_verification",
        email_verified_at=None,
    )
    migration = importlib.import_module(
        "apps.accounts.migrations.0008_repair_legacy_active_accounts"
    )

    migration.repair_legacy_active_accounts(apps, None)
    migration.repair_legacy_active_accounts(apps, None)

    advisor.refresh_from_db()
    administrator.refresh_from_db()
    pending.refresh_from_db()
    assert advisor.requested_role == "teacher"
    assert advisor.active_role == "teacher"
    assert advisor.email_verified_at is not None
    assert TeacherProfile.objects.filter(user=advisor).exists()
    assert administrator.requested_role == "administrator"
    assert administrator.active_role == "administrator"
    assert administrator.email_verified_at is not None
    assert pending.email_verified_at is None
