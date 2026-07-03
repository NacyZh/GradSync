from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):
    initial = True

    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.CreateModel(
            name="UploadedFile",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("category", models.CharField(choices=[("paper", "Paper"), ("code", "Code archive"), ("document", "Document"), ("writing", "Writing"), ("feedback", "Feedback")], max_length=20)),
                ("original_filename", models.CharField(max_length=255)),
                ("stored_name", models.CharField(max_length=512)),
                ("content_type", models.CharField(blank=True, max_length=120)),
                ("size_bytes", models.PositiveBigIntegerField()),
                ("checksum_sha256", models.CharField(db_index=True, max_length=64)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("owner", models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, related_name="uploaded_files", to=settings.AUTH_USER_MODEL)),
            ],
            options={"ordering": ["-created_at"]},
        ),
        migrations.AddIndex(
            model_name="uploadedfile",
            index=models.Index(fields=["category", "created_at"], name="common_upload_category_idx"),
        ),
        migrations.AddIndex(
            model_name="uploadedfile",
            index=models.Index(fields=["owner", "category"], name="common_upload_owner_idx"),
        ),
    ]
