import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("projects", "0001_initial"),
        ("repositories", "0002_code_archive_visibility"),
    ]

    operations = [
        migrations.AddField(
            model_name="codeartifact",
            name="boundary_classification",
            field=models.CharField(
                choices=[
                    ("standalone_shared", "Standalone shared"),
                    ("project_material", "Project material"),
                    ("pending_review", "Pending review"),
                ],
                db_index=True,
                default="standalone_shared",
                max_length=30,
            ),
        ),
        migrations.AddField(
            model_name="codeartifact",
            name="source_project",
            field=models.ForeignKey(
                blank=True,
                null=True,
                on_delete=django.db.models.deletion.SET_NULL,
                related_name="source_code_artifacts",
                to="projects.researchproject",
            ),
        ),
        migrations.AddField(
            model_name="codeartifact",
            name="migrated_from_project_nested_area",
            field=models.BooleanField(default=False),
        ),
        migrations.AddField(
            model_name="codeartifact",
            name="classification_reason",
            field=models.CharField(
                choices=[
                    ("previous_functional_area", "Previous functional area"),
                    ("explicit_project_specific", "Explicit project-specific"),
                    ("ambiguous_legacy", "Ambiguous legacy"),
                    ("manual_review", "Manual review"),
                    ("system_default", "System default"),
                ],
                default="previous_functional_area",
                max_length=40,
            ),
        ),
        migrations.AddIndex(
            model_name="codeartifact",
            index=models.Index(
                fields=["boundary_classification", "visibility", "status"],
                name="repo_code_boundary_idx",
            ),
        ),
        migrations.AddIndex(
            model_name="codeartifact",
            index=models.Index(
                fields=["source_project", "boundary_classification", "status"],
                name="repo_code_source_idx",
            ),
        ),
    ]
