from datetime import date

import pytest
from rest_framework.test import APIClient

from apps.library.models import DocumentRecord, PaperRecord
from apps.repositories.models import CodeArtifact
from apps.submissions.models import WeeklyProgressReport
from apps.tasks.models import Task
from tests.factories.accounts import RestrictedUserFactory, UserFactory
from tests.factories.collaboration import (
    CodeArtifactFactory,
    DocumentRecordFactory,
    PaperRecordFactory,
    ProjectMembershipFactory,
    ResearchProjectFactory,
)


@pytest.mark.django_db
def test_global_search_returns_all_visible_domains_without_hidden_project_metadata():
    user = UserFactory(name="Search User")
    visible_project = ResearchProjectFactory(title="Helix Visible Project")
    hidden_project = ResearchProjectFactory(title="Helix Hidden Project")
    ProjectMembershipFactory(project=visible_project, user=user)

    visible_member = UserFactory(name="Visible Member", nickname="helixmember")
    hidden_member = UserFactory(name="Hidden Member", nickname="helixmember-hidden")
    ProjectMembershipFactory(project=visible_project, user=visible_member)
    ProjectMembershipFactory(project=hidden_project, user=hidden_member)

    visible_task = Task.objects.create(
        project=visible_project,
        title="Helix Task",
        description="Visible task",
        created_by=visible_project.advisor,
    )
    hidden_task = Task.objects.create(
        project=hidden_project,
        title="Helix Hidden Task",
        description="Hidden task",
        created_by=hidden_project.advisor,
    )
    visible_report = WeeklyProgressReport.objects.create(
        project=visible_project,
        student=user,
        report_week_start=date(2026, 7, 20),
        completed_work="Helix report progress",
        next_steps="Continue",
    )
    hidden_report = WeeklyProgressReport.objects.create(
        project=hidden_project,
        student=hidden_member,
        report_week_start=date(2026, 7, 20),
        completed_work="Helix hidden report",
        next_steps="Continue",
    )
    visible_paper = PaperRecordFactory(
        project=visible_project,
        title="Helix Paper",
        boundary_classification=PaperRecord.BoundaryClassification.PROJECT_MATERIAL,
        visibility=PaperRecord.Visibility.PROJECT_MEMBERS,
    )
    hidden_paper = PaperRecordFactory(
        project=hidden_project,
        title="Helix Hidden Paper",
        boundary_classification=PaperRecord.BoundaryClassification.PROJECT_MATERIAL,
        visibility=PaperRecord.Visibility.PROJECT_MEMBERS,
    )
    visible_document = DocumentRecordFactory(
        project=visible_project,
        title="Helix Document",
        boundary_classification=DocumentRecord.BoundaryClassification.PROJECT_MATERIAL,
        visibility=DocumentRecord.Visibility.PROJECT_MEMBERS,
    )
    hidden_document = DocumentRecordFactory(
        project=hidden_project,
        title="Helix Hidden Document",
        boundary_classification=DocumentRecord.BoundaryClassification.PROJECT_MATERIAL,
        visibility=DocumentRecord.Visibility.PROJECT_MEMBERS,
    )
    visible_code = CodeArtifactFactory(
        project=visible_project,
        name="Helix Code",
        boundary_classification=CodeArtifact.BoundaryClassification.PROJECT_MATERIAL,
        visibility=CodeArtifact.Visibility.PROJECT_MEMBERS,
    )
    hidden_code = CodeArtifactFactory(
        project=hidden_project,
        name="Helix Hidden Code",
        boundary_classification=CodeArtifact.BoundaryClassification.PROJECT_MATERIAL,
        visibility=CodeArtifact.Visibility.PROJECT_MEMBERS,
    )

    client = APIClient()
    client.force_authenticate(user)
    response = client.get("/api/search/", {"q": "Helix", "limit": 10})

    assert response.status_code == 200
    results = response.json()["results"]
    result_ids = {result["id"] for result in results}
    assert {
        f"project:{visible_project.id}",
        f"task:{visible_task.id}",
        f"report:{visible_report.id}",
        f"paper:{visible_paper.id}",
        f"document:{visible_document.id}",
        f"code:{visible_code.id}",
        f"member:{visible_project.memberships.get(user=visible_member).id}",
    }.issubset(result_ids)
    assert {
        f"project:{hidden_project.id}",
        f"task:{hidden_task.id}",
        f"report:{hidden_report.id}",
        f"paper:{hidden_paper.id}",
        f"document:{hidden_document.id}",
        f"code:{hidden_code.id}",
        f"member:{hidden_project.memberships.get(user=hidden_member).id}",
    }.isdisjoint(result_ids)
    assert "Helix Hidden Project" not in response.content.decode()
    assert all("@" not in result["context"] for result in results)


@pytest.mark.django_db
def test_global_search_includes_group_shared_materials_without_project_membership():
    user = UserFactory()
    unrelated_project = ResearchProjectFactory()
    paper = PaperRecordFactory(
        project=unrelated_project,
        title="Shared Spectroscopy Paper",
        boundary_classification=PaperRecord.BoundaryClassification.STANDALONE_SHARED,
    )

    client = APIClient()
    client.force_authenticate(user)
    response = client.get("/api/search/", {"q": "Spectroscopy"})

    assert response.status_code == 200
    assert f"paper:{paper.id}" in {result["id"] for result in response.json()["results"]}


@pytest.mark.django_db
def test_global_search_validates_query_and_rejects_inactive_accounts():
    active_client = APIClient()
    active_client.force_authenticate(UserFactory())
    invalid_response = active_client.get("/api/search/", {"q": "x"})
    assert invalid_response.status_code == 400

    restricted_client = APIClient()
    restricted_client.force_authenticate(RestrictedUserFactory())
    restricted_response = restricted_client.get("/api/search/", {"q": "project"})
    assert restricted_response.status_code == 403
