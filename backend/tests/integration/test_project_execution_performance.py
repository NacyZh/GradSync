from datetime import timedelta

import pytest
from django.db import connection
from django.test.utils import CaptureQueriesContext
from django.utils import timezone
from rest_framework.test import APIClient

from apps.projects.models import Deliverable, Milestone, ProjectMembership
from tests.factories.accounts import VerifiedUserFactory
from tests.factories.collaboration import ProjectMembershipFactory, ResearchProjectFactory


@pytest.mark.django_db
def test_execution_list_is_bounded_for_two_hundred_records():
    advisor = VerifiedUserFactory(global_role="advisor", active_role="teacher")
    project = ResearchProjectFactory(advisor=advisor)
    ProjectMembershipFactory(
        project=project, user=advisor, role=ProjectMembership.Role.ADVISOR
    )
    milestone = Milestone.objects.create(
        project=project,
        title="Scale",
        target_date=timezone.localdate() + timedelta(days=30),
        order=0,
        created_by=advisor,
    )
    Deliverable.objects.bulk_create(
        [
            Deliverable(
                project=project,
                milestone=milestone,
                title=f"Output {index}",
                acceptance_criteria="Complete.",
                due_date=timezone.localdate() + timedelta(days=index % 30),
                order=index,
                created_by=advisor,
            )
            for index in range(200)
        ]
    )
    client = APIClient()
    client.force_authenticate(advisor)
    with CaptureQueriesContext(connection) as queries:
        response = client.get(f"/api/projects/{project.id}/deliverables/?pageSize=50")
    assert response.status_code == 200
    assert len(response.data["results"]) == 50
    assert response.data["page"]["nextCursor"] is not None
    assert len(queries) < 80
