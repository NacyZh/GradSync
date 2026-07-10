from django.db import migrations


def forwards(apps, schema_editor):
    for model_name in ("PaperRecord", "DocumentRecord"):
        model = apps.get_model("library", model_name)
        model.objects.filter(boundary_classification="standalone_shared").update(
            visibility="group_wide",
            source_project=None,
            classification_reason="previous_functional_area",
        )
        model.objects.filter(boundary_classification="pending_review").update(
            visibility="project_members",
            classification_reason="ambiguous_legacy",
        )


def backwards(apps, schema_editor):
    pass


class Migration(migrations.Migration):
    dependencies = [
        ("library", "0007_shared_workspace_boundaries"),
    ]

    operations = [
        migrations.RunPython(forwards, backwards),
    ]
