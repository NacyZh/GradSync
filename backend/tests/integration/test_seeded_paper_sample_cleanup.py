import pytest
from django.core.management import call_command

from apps.library.models import PaperRecord
from tests.factories.collaboration import PaperRecordFactory

pytestmark = pytest.mark.django_db


def test_remove_seeded_paper_samples_deletes_validation_and_e2e_seeded_papers():
    seeded_title = PaperRecordFactory(
        title="Graph Neural Methods",
        canonical_title="Graph Neural Methods",
        source_path_label="custom-user-path",
    )
    seeded_path = PaperRecordFactory(
        title="Different Title",
        canonical_title="Different Title",
        source_path_label="team-library/materials-gnn",
    )
    user_paper = PaperRecordFactory(
        title="User Research Paper",
        canonical_title="User Research Paper",
        source_path_label="team-library/user-upload",
    )

    call_command("remove_seeded_paper_samples", verbosity=0)

    assert not PaperRecord.objects.filter(pk=seeded_title.pk).exists()
    assert not PaperRecord.objects.filter(pk=seeded_path.pk).exists()
    assert PaperRecord.objects.filter(pk=user_paper.pk).exists()
