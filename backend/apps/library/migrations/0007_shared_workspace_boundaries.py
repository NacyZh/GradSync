import django.db.models.deletion
from django.conf import settings
from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
        ("projects", "0001_initial"),
        ("library", "0006_paper_file_actions_foundation"),
    ]

    operations = [
        migrations.AddField(
            model_name="paperrecord",
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
            model_name="paperrecord",
            name="source_project",
            field=models.ForeignKey(
                blank=True,
                null=True,
                on_delete=django.db.models.deletion.SET_NULL,
                related_name="source_paper_records",
                to="projects.researchproject",
            ),
        ),
        migrations.AddField(
            model_name="paperrecord",
            name="migrated_from_project_nested_area",
            field=models.BooleanField(default=False),
        ),
        migrations.AddField(
            model_name="paperrecord",
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
        migrations.AddField(
            model_name="documentrecord",
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
            model_name="documentrecord",
            name="source_project",
            field=models.ForeignKey(
                blank=True,
                null=True,
                on_delete=django.db.models.deletion.SET_NULL,
                related_name="source_document_records",
                to="projects.researchproject",
            ),
        ),
        migrations.AddField(
            model_name="documentrecord",
            name="migrated_from_project_nested_area",
            field=models.BooleanField(default=False),
        ),
        migrations.AddField(
            model_name="documentrecord",
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
            model_name="paperrecord",
            index=models.Index(
                fields=["boundary_classification", "visibility", "status"],
                name="library_paper_boundary_idx",
            ),
        ),
        migrations.AddIndex(
            model_name="paperrecord",
            index=models.Index(
                fields=["source_project", "boundary_classification", "status"],
                name="library_paper_source_idx",
            ),
        ),
        migrations.AddIndex(
            model_name="documentrecord",
            index=models.Index(
                fields=["boundary_classification", "visibility", "status"],
                name="library_doc_boundary_idx",
            ),
        ),
        migrations.AddIndex(
            model_name="documentrecord",
            index=models.Index(
                fields=["source_project", "boundary_classification", "status"],
                name="library_doc_source_idx",
            ),
        ),
    ]
