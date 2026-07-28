from datetime import timedelta

import pytest
from django.utils import timezone
from rest_framework.test import APIClient

from apps.projects.models import ProjectMembership
from tests.factories.accounts import VerifiedUserFactory
from tests.factories.collaboration import ProjectMembershipFactory, ResearchProjectFactory


@pytest.fixture
def execution_api():
    advisor = VerifiedUserFactory(global_role="advisor", active_role="teacher")
    student = VerifiedUserFactory(global_role="student", active_role="student")
    project = ResearchProjectFactory(advisor=advisor)
    ProjectMembershipFactory(
        project=project, user=advisor, role=ProjectMembership.Role.ADVISOR
    )
    ProjectMembershipFactory(
        project=project, user=student, role=ProjectMembership.Role.STUDENT
    )
    client = APIClient()
    client.force_authenticate(advisor)
    return client, project, advisor, student


@pytest.mark.django_db
def test_execution_summary_and_milestone_contract(execution_api):
    client, project, _advisor, student = execution_api
    summary = client.get(f"/api/projects/{project.id}/execution-summary/")
    assert summary.status_code == 200
    assert summary.data["projectId"] == project.id
    assert summary.data["capabilities"]["canManageMilestones"] is True

    created = client.post(
        f"/api/projects/{project.id}/milestones/",
        {
            "title": "Validated prototype",
            "description": "Reproducible output.",
            "targetDate": str(timezone.localdate() + timedelta(days=7)),
            "ownerIds": [student.id],
        },
        format="json",
    )
    assert created.status_code == 201
    assert created.data["status"] == "planned"
    listed = client.get(
        f"/api/projects/{project.id}/milestones/?pageSize=25&q=prototype"
    )
    assert listed.status_code == 200
    assert listed.data["page"]["nextCursor"] is None
    assert listed.data["results"][0]["ownerIds"] == [student.id]


@pytest.mark.django_db
def test_deliverable_submit_and_conflict_contract(execution_api):
    client, project, _advisor, student = execution_api
    milestone = client.post(
        f"/api/projects/{project.id}/milestones/",
        {
            "title": "Dataset",
            "targetDate": str(timezone.localdate() + timedelta(days=7)),
            "ownerIds": [student.id],
        },
        format="json",
    ).data
    created = client.post(
        f"/api/projects/{project.id}/deliverables/",
        {
            "milestoneId": milestone["id"],
            "title": "Curated dataset",
            "acceptanceCriteria": "Dataset and provenance are available.",
            "dueDate": str(timezone.localdate() + timedelta(days=5)),
            "required": True,
            "assigneeIds": [student.id],
        },
        format="json",
    )
    assert created.status_code == 201
    deliverable = created.data

    stale = client.patch(
        f"/api/projects/{project.id}/deliverables/{deliverable['id']}/",
        {"expectedVersion": 999, "progressPercent": 25},
        format="json",
    )
    assert stale.status_code == 409
    assert "message" in stale.data

    client.force_authenticate(student)
    submitted = client.post(
        f"/api/projects/{project.id}/deliverables/{deliverable['id']}/submit/",
        {
            "expectedVersion": deliverable["version"],
            "description": "Dataset snapshot.",
            "evidence": [
                {
                    "type": "external_url",
                    "url": "https://example.test/data",
                    "label": "Dataset",
                }
            ],
            "idempotencyKey": "submission-001",
        },
        format="json",
    )
    assert submitted.status_code == 201
    assert submitted.data["revisionNumber"] == 1
    assert submitted.data["evidence"][0]["available"] is True
