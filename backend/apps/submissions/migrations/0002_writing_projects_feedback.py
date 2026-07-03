import django.db.models.deletion
from django.conf import settings
from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("common", "0002_uploaded_file"),
        ("notifications", "0002_notification_metadata"),
        ("projects", "0001_initial"),
        ("submissions", "0001_initial"),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.CreateModel(
            name="WritingProject",
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
                ("title", models.CharField(max_length=255)),
                (
                    "writing_type",
                    models.CharField(
                        choices=[
                            ("thesis", "Thesis"),
                            ("manuscript", "Manuscript"),
                            ("paper", "Paper"),
                            ("other", "Other"),
                        ],
                        max_length=30,
                    ),
                ),
                (
                    "status",
                    models.CharField(
                        choices=[
                            ("active", "Active"),
                            ("closed", "Closed"),
                            ("archived", "Archived"),
                        ],
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
                        related_name="writing_projects",
                        to="projects.researchproject",
                    ),
                ),
                (
                    "student",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.PROTECT,
                        related_name="writing_projects",
                        to=settings.AUTH_USER_MODEL,
                    ),
                ),
            ],
            options={"ordering": ["title", "-created_at"]},
        ),
        migrations.CreateModel(
            name="WritingVersion",
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
                ("version_number", models.PositiveIntegerField()),
                (
                    "file_kind",
                    models.CharField(
                        choices=[
                            ("word", "Word document"),
                            ("latex_source", "LaTeX source"),
                            ("latex_archive", "LaTeX archive"),
                        ],
                        max_length=30,
                    ),
                ),
                ("summary", models.TextField(blank=True)),
                (
                    "status",
                    models.CharField(
                        choices=[
                            ("submitted", "Submitted"),
                            ("under_review", "Under review"),
                            ("feedback_available", "Feedback available"),
                            ("closed", "Closed"),
                        ],
                        default="submitted",
                        max_length=30,
                    ),
                ),
                ("submitted_at", models.DateTimeField(auto_now_add=True)),
                (
                    "draft_file",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.PROTECT,
                        related_name="writing_versions",
                        to="common.uploadedfile",
                    ),
                ),
                (
                    "submitted_by",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.PROTECT,
                        related_name="writing_versions",
                        to=settings.AUTH_USER_MODEL,
                    ),
                ),
                (
                    "writing_project",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="versions",
                        to="submissions.writingproject",
                    ),
                ),
            ],
            options={
                "ordering": ["-version_number"],
                "unique_together": {("writing_project", "version_number")},
            },
        ),
        migrations.CreateModel(
            name="TeacherFeedback",
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
                ("comments", models.TextField(blank=True)),
                (
                    "status",
                    models.CharField(
                        choices=[
                            ("draft", "Draft"),
                            ("submitted", "Submitted"),
                            ("notification_pending", "Notification pending"),
                            ("notification_sent", "Notification sent"),
                            ("notification_failed", "Notification failed"),
                        ],
                        default="notification_pending",
                        max_length=30,
                    ),
                ),
                ("submitted_at", models.DateTimeField(auto_now_add=True)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                (
                    "annotated_file",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.PROTECT,
                        related_name="teacher_feedback",
                        to="common.uploadedfile",
                    ),
                ),
                (
                    "notification",
                    models.ForeignKey(
                        blank=True,
                        null=True,
                        on_delete=django.db.models.deletion.SET_NULL,
                        related_name="teacher_feedback",
                        to="notifications.notification",
                    ),
                ),
                (
                    "reviewer",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.PROTECT,
                        related_name="teacher_feedback",
                        to=settings.AUTH_USER_MODEL,
                    ),
                ),
                (
                    "writing_version",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="feedback",
                        to="submissions.writingversion",
                    ),
                ),
            ],
            options={"ordering": ["-submitted_at"]},
        ),
        migrations.AddIndex(
            model_name="writingproject",
            index=models.Index(
                fields=["project", "student", "status"], name="sub_writing_scope_idx"
            ),
        ),
        migrations.AddIndex(
            model_name="writingproject",
            index=models.Index(fields=["project", "title"], name="sub_writing_title_idx"),
        ),
        migrations.AddIndex(
            model_name="writingversion",
            index=models.Index(
                fields=["writing_project", "version_number"], name="sub_writing_version_idx"
            ),
        ),
        migrations.AddIndex(
            model_name="writingversion",
            index=models.Index(fields=["status", "submitted_at"], name="sub_writing_status_idx"),
        ),
        migrations.AddIndex(
            model_name="teacherfeedback",
            index=models.Index(
                fields=["writing_version", "submitted_at"], name="sub_feedback_version_idx"
            ),
        ),
        migrations.AddIndex(
            model_name="teacherfeedback",
            index=models.Index(
                fields=["reviewer", "submitted_at"], name="sub_feedback_reviewer_idx"
            ),
        ),
    ]
