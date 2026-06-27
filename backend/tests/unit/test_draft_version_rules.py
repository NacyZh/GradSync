import pytest

from apps.projects.models import ProjectMembership, ResearchProject
from apps.submissions.draft_services import DraftService
from tests.factories.accounts import UserFactory


@pytest.mark.django_db
def test_draft_versions_increment():
    student = UserFactory(global_role="student")
    advisor = UserFactory(global_role="advisor")
    project = ResearchProject.objects.create(title="Project", advisor=advisor)
    ProjectMembership.objects.create(project=project, user=student, role="student")
    service = DraftService(student, project)
    draft = service.create_draft(title="Paper")

    first = service.submit_version(draft=draft, content_reference="v1")
    second = service.submit_version(draft=draft, content_reference="v2")

    assert first.version_number == 1
    assert second.version_number == 2
