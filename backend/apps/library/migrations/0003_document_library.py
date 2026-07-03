import django.db.models.deletion
from django.conf import settings
from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("common", "0002_uploaded_file"),
        ("library", "0002_paper_visibility_uploaded_file"),
        ("projects", "0001_initial"),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.CreateModel(
            name="DocumentCategory",
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
                ("name", models.CharField(max_length=120, unique=True)),
                ("description", models.TextField(blank=True)),
                (
                    "status",
                    models.CharField(
                        choices=[("active", "Active"), ("archived", "Archived")],
                        default="active",
                        max_length=20,
                    ),
                ),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                (
                    "created_by",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.PROTECT,
                        related_name="document_categories",
                        to=settings.AUTH_USER_MODEL,
                    ),
                ),
            ],
            options={"ordering": ["name"]},
        ),
        migrations.CreateModel(
            name="DocumentRecord",
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
                    "visibility",
                    models.CharField(
                        choices=[
                            ("project_members", "Project members"),
                            ("group_wide", "Group-wide"),
                        ],
                        default="project_members",
                        max_length=30,
                    ),
                ),
                ("visibility_changed_at", models.DateTimeField(blank=True, null=True)),
                ("title", models.CharField(max_length=255)),
                ("description", models.TextField(blank=True)),
                ("checksum_sha256", models.CharField(db_index=True, max_length=64)),
                (
                    "status",
                    models.CharField(
                        choices=[("active", "Active"), ("archived", "Archived")],
                        default="active",
                        max_length=20,
                    ),
                ),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                (
                    "category",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.PROTECT,
                        related_name="documents",
                        to="library.documentcategory",
                    ),
                ),
                (
                    "created_by",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.PROTECT,
                        related_name="document_records",
                        to=settings.AUTH_USER_MODEL,
                    ),
                ),
                (
                    "document_file",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.PROTECT,
                        related_name="document_records",
                        to="common.uploadedfile",
                    ),
                ),
                (
                    "project",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="document_records",
                        to="projects.researchproject",
                    ),
                ),
                (
                    "visibility_changed_by",
                    models.ForeignKey(
                        blank=True,
                        null=True,
                        on_delete=django.db.models.deletion.SET_NULL,
                        related_name="document_visibility_changes",
                        to=settings.AUTH_USER_MODEL,
                    ),
                ),
            ],
            options={"ordering": ["title"]},
        ),
        migrations.AddIndex(
            model_name="documentcategory",
            index=models.Index(fields=["status", "name"], name="library_doccat_status_idx"),
        ),
        migrations.AddIndex(
            model_name="documentrecord",
            index=models.Index(
                fields=["project", "visibility", "status"], name="library_doc_scope_idx"
            ),
        ),
        migrations.AddIndex(
            model_name="documentrecord",
            index=models.Index(
                fields=["project", "category", "title"], name="library_doc_category_idx"
            ),
        ),
        migrations.AddIndex(
            model_name="documentrecord",
            index=models.Index(
                fields=["created_by", "created_at"], name="library_doc_uploader_idx"
            ),
        ),
    ]
