import pytest

from apps.projects.material_services import (
    BoundaryClassification,
    classify_workspace_record,
    is_externally_shared_record,
)
from tests.factories.collaboration import PaperRecordFactory
from tests.factories.shared_workspace import pending_review_paper, project_with_members


@pytest.mark.django_db
def test_previous_functional_records_default_to_standalone_shared():
    paper = PaperRecordFactory()

    classification = classify_workspace_record(paper)

    assert classification.boundary_type == BoundaryClassification.STANDALONE_SHARED
    assert classification.visibility == "group_wide"
    assert classification.pending_review is False
    assert is_externally_shared_record(paper)


@pytest.mark.django_db
def test_ambiguous_records_remain_pending_and_project_associated():
    project = project_with_members()
    paper = pending_review_paper(project)

    classification = classify_workspace_record(paper)

    assert classification.boundary_type == BoundaryClassification.PENDING_REVIEW
    assert classification.source_project_id == project.id
    assert classification.pending_review is True
    assert not is_externally_shared_record(paper)
