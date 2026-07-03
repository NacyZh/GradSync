import django.db.models.deletion
from django.conf import settings
from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("common", "0002_uploaded_file"),
        ("library", "0001_initial"),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.AddField(
            model_name="paperrecord",
            name="visibility",
            field=models.CharField(
                choices=[
                    ("project_members", "Project members"),
                    ("group_wide", "Group-wide"),
                ],
                default="project_members",
                max_length=30,
            ),
        ),
        migrations.AddField(
            model_name="paperrecord",
            name="visibility_changed_by",
            field=models.ForeignKey(
                blank=True,
                null=True,
                on_delete=django.db.models.deletion.SET_NULL,
                related_name="paper_visibility_changes",
                to=settings.AUTH_USER_MODEL,
            ),
        ),
        migrations.AddField(
            model_name="paperrecord",
            name="visibility_changed_at",
            field=models.DateTimeField(blank=True, null=True),
        ),
        migrations.AddField(
            model_name="paperrecord",
            name="uploaded_file",
            field=models.ForeignKey(
                blank=True,
                null=True,
                on_delete=django.db.models.deletion.PROTECT,
                related_name="paper_records",
                to="common.uploadedfile",
            ),
        ),
        migrations.AddField(
            model_name="paperrecord",
            name="checksum_sha256",
            field=models.CharField(blank=True, db_index=True, max_length=64),
        ),
        migrations.AddIndex(
            model_name="paperrecord",
            index=models.Index(
                fields=["project", "visibility", "status"], name="library_paper_scope_idx"
            ),
        ),
        migrations.AddIndex(
            model_name="paperrecord",
            index=models.Index(
                fields=["project", "publication_year"],
                name="library_paper_year_idx",
            ),
        ),
        migrations.AddIndex(
            model_name="paperrecord",
            index=models.Index(fields=["project", "title"], name="library_paper_title_idx"),
        ),
        migrations.AddIndex(
            model_name="paperrecord",
            index=models.Index(
                fields=["created_by", "created_at"],
                name="library_paper_uploader_idx",
            ),
        ),
    ]
