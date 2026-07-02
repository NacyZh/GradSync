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
            name="PaperRecord",
            fields=[
                (
                    "id",
                    models.BigAutoField(
                        auto_created=True, primary_key=True, serialize=False, verbose_name="ID"
                    ),
                ),
                ("title", models.CharField(max_length=500)),
                ("authors", models.JSONField(blank=True, default=list)),
                ("venue", models.CharField(blank=True, max_length=255)),
                ("publication_year", models.IntegerField(blank=True, null=True)),
                ("doi", models.CharField(blank=True, max_length=255)),
                ("external_ids", models.JSONField(blank=True, default=dict)),
                ("abstract", models.TextField(blank=True)),
                ("notes", models.TextField(blank=True)),
                ("tags", models.JSONField(blank=True, default=list)),
                (
                    "import_source",
                    models.CharField(
                        choices=[
                            ("manual", "Manual"),
                            ("doi", "DOI"),
                            ("bibtex", "BibTeX"),
                            ("file_metadata", "File metadata"),
                            ("batch", "Batch"),
                        ],
                        default="manual",
                        max_length=30,
                    ),
                ),
                ("fingerprint", models.CharField(blank=True, max_length=600)),
                (
                    "status",
                    models.CharField(
                        choices=[
                            ("active", "Active"),
                            ("duplicate_blocked", "Duplicate blocked"),
                            ("archived", "Archived"),
                        ],
                        default="active",
                        max_length=30,
                    ),
                ),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                ("archived_at", models.DateTimeField(blank=True, null=True)),
                (
                    "created_by",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.PROTECT, to=settings.AUTH_USER_MODEL
                    ),
                ),
                (
                    "project",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="paper_records",
                        to="projects.researchproject",
                    ),
                ),
            ],
            options={"ordering": ["title"]},
        ),
        migrations.CreateModel(
            name="PaperImportBatch",
            fields=[
                (
                    "id",
                    models.BigAutoField(
                        auto_created=True, primary_key=True, serialize=False, verbose_name="ID"
                    ),
                ),
                (
                    "source_type",
                    models.CharField(
                        choices=[
                            ("file", "File"),
                            ("doi", "DOI"),
                            ("bibtex", "BibTeX"),
                            ("mixed", "Mixed"),
                        ],
                        max_length=20,
                    ),
                ),
                (
                    "status",
                    models.CharField(
                        choices=[
                            ("staged", "Staged"),
                            ("committed", "Committed"),
                            ("failed", "Failed"),
                            ("cancelled", "Cancelled"),
                        ],
                        default="staged",
                        max_length=20,
                    ),
                ),
                ("total_items", models.PositiveIntegerField(default=0)),
                ("accepted_count", models.PositiveIntegerField(default=0)),
                ("duplicate_count", models.PositiveIntegerField(default=0)),
                ("error_count", models.PositiveIntegerField(default=0)),
                ("result_summary", models.JSONField(blank=True, default=list)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("committed_at", models.DateTimeField(blank=True, null=True)),
                (
                    "project",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="paper_import_batches",
                        to="projects.researchproject",
                    ),
                ),
                (
                    "requested_by",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.PROTECT, to=settings.AUTH_USER_MODEL
                    ),
                ),
            ],
            options={"ordering": ["-created_at"]},
        ),
        migrations.CreateModel(
            name="PaperAttachment",
            fields=[
                (
                    "id",
                    models.BigAutoField(
                        auto_created=True, primary_key=True, serialize=False, verbose_name="ID"
                    ),
                ),
                ("storage_key", models.CharField(max_length=500)),
                ("filename", models.CharField(max_length=255)),
                ("content_type", models.CharField(blank=True, max_length=120)),
                ("size_bytes", models.PositiveBigIntegerField(default=0)),
                ("checksum_sha256", models.CharField(max_length=64)),
                (
                    "status",
                    models.CharField(
                        choices=[
                            ("active", "Active"),
                            ("replaced", "Replaced"),
                            ("archived", "Archived"),
                        ],
                        default="active",
                        max_length=20,
                    ),
                ),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                (
                    "paper",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="attachments",
                        to="library.paperrecord",
                    ),
                ),
                (
                    "project",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="paper_attachments",
                        to="projects.researchproject",
                    ),
                ),
                (
                    "uploaded_by",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.PROTECT, to=settings.AUTH_USER_MODEL
                    ),
                ),
            ],
            options={"ordering": ["-created_at"]},
        ),
    ]
