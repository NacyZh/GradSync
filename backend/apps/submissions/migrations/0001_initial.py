import django.db.models.deletion
from django.conf import settings
from django.db import migrations, models


class Migration(migrations.Migration):
    initial = True

    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
        ("projects", "0001_initial"),
    ]

    operations = [
        migrations.CreateModel(
            name="Draft",
            fields=[
                (
                    "id",
                    models.BigAutoField(
                        auto_created=True, primary_key=True, serialize=False, verbose_name="ID"
                    ),
                ),
                ("title", models.CharField(max_length=255)),
                (
                    "status",
                    models.CharField(
                        choices=[("active", "Active"), ("closed", "Closed")],
                        default="active",
                        max_length=20,
                    ),
                ),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                (
                    "project",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="drafts",
                        to="projects.researchproject",
                    ),
                ),
                (
                    "student",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.PROTECT,
                        related_name="drafts",
                        to=settings.AUTH_USER_MODEL,
                    ),
                ),
            ],
        ),
        migrations.CreateModel(
            name="DraftVersion",
            fields=[
                (
                    "id",
                    models.BigAutoField(
                        auto_created=True, primary_key=True, serialize=False, verbose_name="ID"
                    ),
                ),
                ("version_number", models.PositiveIntegerField()),
                ("content_reference", models.CharField(max_length=512)),
                ("summary", models.TextField(blank=True)),
                (
                    "review_status",
                    models.CharField(
                        choices=[
                            ("pending_review", "Pending review"),
                            ("reviewed", "Reviewed"),
                            ("needs_revision", "Needs revision"),
                            ("closed", "Closed"),
                        ],
                        default="pending_review",
                        max_length=30,
                    ),
                ),
                ("submitted_at", models.DateTimeField(auto_now_add=True)),
                ("reviewed_at", models.DateTimeField(blank=True, null=True)),
                (
                    "draft",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="versions",
                        to="submissions.draft",
                    ),
                ),
                (
                    "project",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="draft_versions",
                        to="projects.researchproject",
                    ),
                ),
                (
                    "submitted_by",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.PROTECT, to=settings.AUTH_USER_MODEL
                    ),
                ),
            ],
            options={
                "ordering": ["-version_number"],
                "unique_together": {("draft", "version_number")},
            },
        ),
        migrations.CreateModel(
            name="WeeklyProgressReport",
            fields=[
                (
                    "id",
                    models.BigAutoField(
                        auto_created=True, primary_key=True, serialize=False, verbose_name="ID"
                    ),
                ),
                ("report_week_start", models.DateField()),
                ("completed_work", models.TextField()),
                ("blockers", models.TextField(blank=True)),
                ("next_steps", models.TextField()),
                ("attachment_reference", models.CharField(blank=True, max_length=512)),
                (
                    "review_status",
                    models.CharField(
                        choices=[
                            ("pending_review", "Pending review"),
                            ("reviewed", "Reviewed"),
                            ("needs_revision", "Needs revision"),
                            ("closed", "Closed"),
                        ],
                        default="pending_review",
                        max_length=30,
                    ),
                ),
                ("submitted_at", models.DateTimeField(auto_now_add=True)),
                ("reviewed_at", models.DateTimeField(blank=True, null=True)),
                (
                    "project",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="weekly_reports",
                        to="projects.researchproject",
                    ),
                ),
                (
                    "student",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.PROTECT,
                        related_name="weekly_reports",
                        to=settings.AUTH_USER_MODEL,
                    ),
                ),
            ],
            options={
                "ordering": ["-report_week_start"],
                "unique_together": {("project", "student", "report_week_start")},
            },
        ),
        migrations.CreateModel(
            name="InlineComment",
            fields=[
                (
                    "id",
                    models.BigAutoField(
                        auto_created=True, primary_key=True, serialize=False, verbose_name="ID"
                    ),
                ),
                (
                    "target_type",
                    models.CharField(
                        choices=[
                            ("draft_version", "Draft version"),
                            ("progress_report", "Progress report"),
                        ],
                        max_length=30,
                    ),
                ),
                ("target_id", models.PositiveIntegerField()),
                ("anchor", models.CharField(max_length=255)),
                ("body", models.TextField()),
                (
                    "status",
                    models.CharField(
                        choices=[("open", "Open"), ("resolved", "Resolved")],
                        default="open",
                        max_length=20,
                    ),
                ),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                ("resolved_at", models.DateTimeField(blank=True, null=True)),
                (
                    "author",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.PROTECT, to=settings.AUTH_USER_MODEL
                    ),
                ),
                (
                    "project",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="inline_comments",
                        to="projects.researchproject",
                    ),
                ),
            ],
        ),
    ]
