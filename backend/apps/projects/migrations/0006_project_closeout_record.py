import django.db.models.deletion
from django.conf import settings
from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("projects", "0005_decisions_and_risks"),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.CreateModel(
            name="ProjectCloseoutRecord",
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
                ("archive_version", models.PositiveIntegerField()),
                ("checklist", models.JSONField(default=dict)),
                ("dispositions", models.JSONField(default=dict)),
                ("snapshot", models.JSONField(default=dict)),
                ("notes", models.TextField(blank=True, max_length=4000)),
                ("archived_at", models.DateTimeField(auto_now_add=True)),
                (
                    "archived_by",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.PROTECT,
                        related_name="project_closeouts",
                        to=settings.AUTH_USER_MODEL,
                    ),
                ),
                (
                    "project",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.PROTECT,
                        related_name="closeout_records",
                        to="projects.researchproject",
                    ),
                ),
            ],
            options={
                "ordering": ["-archive_version"],
                "indexes": [
                    models.Index(
                        fields=["project", "-archived_at"],
                        name="project_closeout_time_idx",
                    )
                ],
                "constraints": [
                    models.UniqueConstraint(
                        fields=("project", "archive_version"),
                        name="unique_project_closeout_version",
                    )
                ],
            },
        ),
    ]
