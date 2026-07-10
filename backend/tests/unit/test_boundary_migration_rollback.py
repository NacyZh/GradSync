import pytest

from apps.projects.material_services import classify_workspace_record, is_externally_shared_record
from tests.factories.shared_workspace import (
    active_teacher,
    group_wide_project_code,
    pending_review_paper,
    project_with_members,
)


@pytest.mark.django_db
def test_boundary_classification_replay_keeps_ambiguous_records_hidden():
    project = project_with_members(advisor=active_teacher())
    paper = pending_review_paper(project)

    classification = classify_workspace_record(paper)

    assert classification.pending_review is True
    assert classification.boundary_type == "pending_review"
    assert is_externally_shared_record(paper) is False


@pytest.mark.django_db
def test_boundary_classification_replay_exposes_group_wide_project_material_with_source():
    project = project_with_members(advisor=active_teacher())
    artifact = group_wide_project_code(project)

    classification = classify_workspace_record(artifact)

    assert classification.boundary_type == "project_material"
    assert classification.visibility == "group_wide"
    assert classification.source_project_id == project.id
    assert is_externally_shared_record(artifact) is True
