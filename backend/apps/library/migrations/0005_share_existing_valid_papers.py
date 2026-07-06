from django.db import migrations
from django.utils import timezone


def _normalize_title(value: str | None) -> str:
    import re

    return re.sub(r"\s+", " ", re.sub(r"[^a-z0-9\s]", " ", (value or "").lower())).strip()


def apply_shared_paper_access(apps, schema_editor):
    PaperRecord = apps.get_model("library", "PaperRecord")
    now = timezone.now()
    valid_papers = PaperRecord.objects.filter(status="active")
    for paper in valid_papers.iterator():
        title = paper.canonical_title or paper.title
        paper.canonical_title = title
        paper.normalized_title = paper.normalized_title or _normalize_title(title)
        paper.title_source = paper.title_source or "legacy"
        paper.title_confidence = paper.title_confidence or "medium"
        paper.visibility = "group_wide"
        paper.migrated_from_legacy_scope = True
        paper.shared_access_started_at = paper.shared_access_started_at or now
        paper.save(
            update_fields=[
                "canonical_title",
                "normalized_title",
                "title_source",
                "title_confidence",
                "visibility",
                "migrated_from_legacy_scope",
                "shared_access_started_at",
            ]
        )


def reverse_shared_paper_access(apps, schema_editor):
    PaperRecord = apps.get_model("library", "PaperRecord")
    PaperRecord.objects.filter(migrated_from_legacy_scope=True).update(
        migrated_from_legacy_scope=False,
        shared_access_started_at=None,
    )


class Migration(migrations.Migration):
    dependencies = [
        ("library", "0004_paper_library_workflow"),
    ]

    operations = [
        migrations.RunPython(apply_shared_paper_access, reverse_shared_paper_access),
    ]
