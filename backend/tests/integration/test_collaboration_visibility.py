import pytest

from apps.common.project_scope import filter_visible_assets
from apps.projects.models import ProjectMembership, ResearchProject
from tests.factories.accounts import UserFactory


class Asset:
    def __init__(self, project, visibility):
        self.project = project
        self.project_id = project.id
        self.visibility = visibility


@pytest.mark.django_db
def test_filter_visible_assets_includes_project_member_and_group_wide_assets():
    teacher = UserFactory(global_role="advisor", status="active")
    student = UserFactory(global_role="student", status="active")
    outsider = UserFactory(global_role="student", status="active")
    project = ResearchProject.objects.create(title="P1", advisor=teacher)
    other_project = ResearchProject.objects.create(title="P2", advisor=teacher)
    ProjectMembership.objects.create(project=project, user=student, role="student")

    scoped = Asset(project, "project_members")
    shared = Asset(other_project, "group_wide")
    hidden = Asset(other_project, "project_members")

    assert filter_visible_assets([scoped, shared, hidden], student) == [scoped, shared]
    assert filter_visible_assets([scoped, shared, hidden], outsider) == [shared]
