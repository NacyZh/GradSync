from datetime import timedelta

import pytest
from django.utils import timezone
from rest_framework.test import APIClient

from apps.projects.models import ProjectMembership
from tests.factories.accounts import VerifiedUserFactory
from tests.factories.collaboration import ProjectMembershipFactory, ResearchProjectFactory


@pytest.mark.django_db
def test_decision_and_risk_contracts():
    advisor = VerifiedUserFactory(global_role="advisor", active_role="teacher")
    project = ResearchProjectFactory(advisor=advisor)
    ProjectMembershipFactory(project=project, user=advisor, role=ProjectMembership.Role.ADVISOR)
    client = APIClient()
    client.force_authenticate(advisor)
    decision = client.post(
        f"/api/projects/{project.id}/decisions/",
        {
            "title": "Adopt protocol",
            "context": "The project needs one protocol.",
            "optionsConsidered": ["Protocol A", "Protocol B"],
            "outcome": "Protocol A",
            "rationale": "Validated in pilot work.",
            "ownerId": advisor.id,
            "effectiveDate": str(timezone.localdate()),
            "idempotencyKey": "decision-api-001",
        },
        format="json",
    )
    assert decision.status_code == 201
    assert decision.data["status"] == "current"
    assert client.get(f"/api/projects/{project.id}/decisions/").status_code == 200

    risk = client.post(
        f"/api/projects/{project.id}/risks/",
        {
            "title": "Recruitment delay",
            "description": "Fewer participants than expected.",
            "idempotencyKey": "risk-api-001",
        },
        format="json",
    )
    assert risk.status_code == 201
    triaged = client.patch(
        f"/api/projects/{project.id}/risks/{risk.data['id']}/",
        {
            "expectedVersion": risk.data["version"],
            "likelihood": "medium",
            "impact": "high",
            "ownerId": advisor.id,
            "treatment": "Open another recruitment channel.",
            "reviewDate": str(timezone.localdate() + timedelta(days=7)),
            "reason": "Advisor triage",
        },
        format="json",
    )
    assert triaged.status_code == 200
    assert triaged.data["severity"] == "high"
