import pytest

from apps.projects.models import ProjectMembership, ResearchProject
from apps.submissions.draft_services import DraftService
from tests.factories.accounts import UserFactory


@pytest.mark.django_db
def test_new_draft_submission_creates_advisor_notification():
    advisor = UserFactory(global_role="advisor")
    student = UserFactory(global_role="student")
    project = ResearchProject.objects.create(title="Project", advisor=advisor)
    ProjectMembership.objects.create(project=project, user=advisor, role="advisor")
    ProjectMembership.objects.create(project=project, user=student, role="student")
    service = DraftService(student, project)
    draft = service.create_draft(title="Paper")

    version = service.submit_version(draft=draft, content_reference="v1")

    assert project.notifications.filter(recipient=advisor, target_id=str(version.id)).exists()
