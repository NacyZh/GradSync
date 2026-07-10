from django.db import migrations


def forwards(apps, schema_editor):
    code_artifact = apps.get_model("repositories", "CodeArtifact")
    code_artifact.objects.filter(boundary_classification="standalone_shared").update(
        visibility="group_wide",
        source_project=None,
        classification_reason="previous_functional_area",
    )
    code_artifact.objects.filter(boundary_classification="pending_review").update(
        visibility="project_members",
        classification_reason="ambiguous_legacy",
    )


def backwards(apps, schema_editor):
    pass


class Migration(migrations.Migration):
    dependencies = [
        ("repositories", "0003_shared_workspace_boundaries"),
    ]

    operations = [
        migrations.RunPython(forwards, backwards),
    ]
