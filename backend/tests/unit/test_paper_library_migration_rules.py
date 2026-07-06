from importlib import import_module

import pytest

from apps.library.models import PaperRecord
from apps.projects.models import ResearchProject
from tests.factories.accounts import UserFactory

migration_0005 = import_module("apps.library.migrations.0005_share_existing_valid_papers")


@pytest.mark.django_db
def test_shared_paper_access_migration_updates_only_valid_active_records():
    user = UserFactory(status="active")
    project = ResearchProject.objects.create(title="Legacy Papers", advisor=user)
    active = PaperRecord.objects.create(
        project=project,
        title="Legacy Active Paper",
        authors=["Ada"],
        created_by=user,
        visibility=PaperRecord.Visibility.PROJECT_MEMBERS,
        status=PaperRecord.Status.ACTIVE,
    )
    deleted = PaperRecord.objects.create(
        project=project,
        title="Deleted Paper",
        authors=["Ada"],
        created_by=user,
        visibility=PaperRecord.Visibility.PROJECT_MEMBERS,
        status=PaperRecord.Status.DELETED,
    )
    invalid = PaperRecord.objects.create(
        project=project,
        title="Invalid Paper",
        authors=["Ada"],
        created_by=user,
        visibility=PaperRecord.Visibility.PROJECT_MEMBERS,
        status=PaperRecord.Status.INVALID,
    )

    migration_0005.apply_shared_paper_access(_CurrentApps(), None)

    active.refresh_from_db()
    deleted.refresh_from_db()
    invalid.refresh_from_db()
    assert active.visibility == PaperRecord.Visibility.GROUP_WIDE
    assert active.migrated_from_legacy_scope is True
    assert active.shared_access_started_at is not None
    assert active.canonical_title == "Legacy Active Paper"
    assert active.normalized_title == "legacy active paper"
    assert deleted.visibility == PaperRecord.Visibility.PROJECT_MEMBERS
    assert deleted.migrated_from_legacy_scope is False
    assert invalid.visibility == PaperRecord.Visibility.PROJECT_MEMBERS
    assert invalid.migrated_from_legacy_scope is False


class _CurrentApps:
    @staticmethod
    def get_model(app_label, model_name):
        assert (app_label, model_name) == ("library", "PaperRecord")
        return PaperRecord
