import django.db.models.deletion
from django.conf import settings
from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
        ("projects", "0001_initial"),
    ]

    operations = [
        migrations.CreateModel(
            name="ProjectMaterial",
            fields=[
                (
                    "id",
                    models.BigAutoField(
                        auto_created=True,
                        primary_key=True,
                        serialize=False,
                        verbose_name="ID",
                    ),
                ),
                (
                    "material_type",
                    models.CharField(
                        choices=[("paper", "Paper"), ("document", "Document"), ("code", "Code")],
                        max_length=20,
                    ),
                ),
                ("backing_record_id", models.PositiveIntegerField()),
                (
                    "visibility_state",
                    models.CharField(
                        choices=[
                            ("project-only", "Project-only"),
                            ("group-wide", "Group-wide"),
                        ],
                        default="project-only",
                        max_length=20,
                    ),
                ),
                (
                    "classification_state",
                    models.CharField(
                        choices=[
                            ("active", "Active"),
                            ("pending_review", "Pending review"),
                            ("archived", "Archived"),
                        ],
                        default="active",
                        max_length=20,
                    ),
                ),
                (
                    "classification_reason",
                    models.CharField(
                        choices=[
                            ("previous_functional_area", "Previous functional area"),
                            ("explicit_project_specific", "Explicit project-specific"),
                            ("ambiguous_legacy", "Ambiguous legacy"),
                            ("manual_review", "Manual review"),
                        ],
                        default="explicit_project_specific",
                        max_length=40,
                    ),
                ),
                ("visibility_changed_at", models.DateTimeField(blank=True, null=True)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                (
                    "created_by",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.PROTECT,
                        related_name="created_project_materials",
                        to=settings.AUTH_USER_MODEL,
                    ),
                ),
                (
                    "source_project",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="materials",
                        to="projects.researchproject",
                    ),
                ),
                (
                    "visibility_changed_by",
                    models.ForeignKey(
                        blank=True,
                        null=True,
                        on_delete=django.db.models.deletion.SET_NULL,
                        related_name="project_material_visibility_changes",
                        to=settings.AUTH_USER_MODEL,
                    ),
                ),
            ],
        ),
        migrations.AddIndex(
            model_name="projectmaterial",
            index=models.Index(
                fields=[
                    "source_project",
                    "material_type",
                    "visibility_state",
                    "classification_state",
                ],
                name="projects_mat_scope_idx",
            ),
        ),
        migrations.AddIndex(
            model_name="projectmaterial",
            index=models.Index(
                fields=["material_type", "visibility_state", "classification_state"],
                name="projects_mat_discovery_idx",
            ),
        ),
        migrations.AddIndex(
            model_name="projectmaterial",
            index=models.Index(
                fields=["visibility_changed_by", "visibility_changed_at"],
                name="projects_mat_vis_actor_idx",
            ),
        ),
    ]
