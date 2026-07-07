from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):
    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
        ("library", "0005_share_existing_valid_papers"),
    ]

    operations = [
        migrations.AddField(
            model_name="paperrecord",
            name="delete_reason",
            field=models.CharField(blank=True, max_length=255),
        ),
        migrations.AddField(
            model_name="paperrecord",
            name="deleted_at",
            field=models.DateTimeField(blank=True, null=True),
        ),
        migrations.AddField(
            model_name="paperrecord",
            name="deleted_by",
            field=models.ForeignKey(
                blank=True,
                null=True,
                on_delete=django.db.models.deletion.SET_NULL,
                related_name="deleted_paper_records",
                to=settings.AUTH_USER_MODEL,
            ),
        ),
        migrations.AlterField(
            model_name="paperlibraryactivity",
            name="action",
            field=models.CharField(
                choices=[
                    ("upload_accepted", "Upload accepted"),
                    ("upload_rejected", "Upload rejected"),
                    ("upload_size_rejected", "Upload size rejected"),
                    ("duplicate_rejected", "Duplicate rejected"),
                    ("maintainer_review_created", "Maintainer review created"),
                    ("paper_renamed", "Paper renamed"),
                    ("paper_rename_rejected", "Paper rename rejected"),
                    ("paper_deleted", "Paper deleted"),
                    ("paper_delete_rejected", "Paper delete rejected"),
                    ("download_started", "Download started"),
                    ("download_failed", "Download failed"),
                    ("unavailable_access", "Unavailable access"),
                    ("migration_shared_access_applied", "Migration shared access applied"),
                ],
                max_length=50,
            ),
        ),
    ]
