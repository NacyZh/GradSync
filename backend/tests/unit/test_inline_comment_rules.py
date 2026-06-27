import pytest
from django.core.exceptions import ValidationError

from apps.projects.models import ProjectMembership, ResearchProject
from apps.submissions.comment_services import InlineCommentService
from apps.submissions.models import Draft, DraftVersion
from tests.factories.accounts import UserFactory


@pytest.mark.django_db
def test_comment_target_must_be_in_same_project():
    advisor = UserFactory(global_role="advisor")
    student = UserFactory(global_role="student")
    project_a = ResearchProject.objects.create(title="A", advisor=advisor)
    project_b = ResearchProject.objects.create(title="B", advisor=advisor)
    ProjectMembership.objects.create(project=project_a, user=advisor, role="advisor")
    draft = Draft.objects.create(project=project_b, student=student, title="Paper")
    version = DraftVersion.objects.create(
        project=project_b,
        draft=draft,
        submitted_by=student,
        version_number=1,
        content_reference="v1",
    )

    with pytest.raises(ValidationError):
        InlineCommentService(advisor, project_a).create_comment(
            target_type="draft_version",
            target_id=version.id,
            anchor="p1",
            body="Nope",
        )
