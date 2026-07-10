import django.db.models.deletion
from django.conf import settings
from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
        ("projects", "0001_initial"),
        ("submissions", "0002_writing_projects_feedback"),
    ]

    operations = [
        migrations.AddField(
            model_name="writingproject",
            name="legacy_project",
            field=models.ForeignKey(
                blank=True,
                null=True,
                on_delete=django.db.models.deletion.SET_NULL,
                related_name="legacy_writing_projects",
                to="projects.researchproject",
            ),
        ),
        migrations.AddField(
            model_name="writingproject",
            name="migrated_from_project_nested_area",
            field=models.BooleanField(default=False),
        ),
        migrations.CreateModel(
            name="WritingParticipant",
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
                    "participant_role",
                    models.CharField(
                        choices=[
                            ("student_author", "Student author"),
                            ("bound_advisor", "Bound advisor"),
                            ("assigned_reviewer", "Assigned reviewer"),
                            ("administrator", "Administrator"),
                        ],
                        max_length=30,
                    ),
                ),
                (
                    "status",
                    models.CharField(
                        choices=[("active", "Active"), ("removed", "Removed")],
                        default="active",
                        max_length=20,
                    ),
                ),
                ("assigned_at", models.DateTimeField(auto_now_add=True)),
                ("removed_at", models.DateTimeField(blank=True, null=True)),
                (
                    "assigned_by",
                    models.ForeignKey(
                        blank=True,
                        null=True,
                        on_delete=django.db.models.deletion.SET_NULL,
                        related_name="assigned_writing_participants",
                        to=settings.AUTH_USER_MODEL,
                    ),
                ),
                (
                    "user",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="writing_participations",
                        to=settings.AUTH_USER_MODEL,
                    ),
                ),
                (
                    "writing_project",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="participants",
                        to="submissions.writingproject",
                    ),
                ),
            ],
        ),
        migrations.AddIndex(
            model_name="writingproject",
            index=models.Index(fields=["student", "status"], name="sub_writing_student_idx"),
        ),
        migrations.AddIndex(
            model_name="writingproject",
            index=models.Index(fields=["legacy_project", "status"], name="sub_writing_legacy_idx"),
        ),
        migrations.AddIndex(
            model_name="writingparticipant",
            index=models.Index(
                fields=["writing_project", "user", "status"],
                name="sub_wpart_project_user_idx",
            ),
        ),
        migrations.AddIndex(
            model_name="writingparticipant",
            index=models.Index(
                fields=["user", "participant_role", "status"],
                name="sub_wpart_role_idx",
            ),
        ),
    ]
