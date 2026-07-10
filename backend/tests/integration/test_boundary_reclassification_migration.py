import pytest
from django.core.management import call_command

from apps.library.models.documents import DocumentRecord
from apps.library.models.papers import PaperRecord
from apps.repositories.models import CodeArtifact
from tests.factories.shared_workspace import (
    active_teacher,
    pending_review_paper,
    project_only_document,
    project_with_members,
    standalone_shared_code,
)


@pytest.mark.django_db
def test_boundary_reclassification_dry_run_keeps_ambiguous_records_hidden(capsys):
    advisor = active_teacher()
    project = project_with_members(advisor=advisor)
    pending_review_paper(project, title="Ambiguous Legacy Paper")
    project_only_document(project, title="Explicit Project Document")
    standalone_shared_code(project=project, name="Standalone Code")

    call_command("reclassify_workspace_boundaries", "--dry-run")
    output = capsys.readouterr().out

    assert "papers_pending_review=1" in output
    assert "documents_project_material=1" in output
    assert "code_standalone_shared=1" in output
    assert (
        PaperRecord.objects.get(title="Ambiguous Legacy Paper").boundary_classification
        == "pending_review"
    )
    assert (
        DocumentRecord.objects.get(title="Explicit Project Document").boundary_classification
        == "project_material"
    )
    assert (
        CodeArtifact.objects.get(name="Standalone Code").boundary_classification
        == "standalone_shared"
    )
