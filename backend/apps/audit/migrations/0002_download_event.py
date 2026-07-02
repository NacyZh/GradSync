import django.db.models.deletion
from django.conf import settings
from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("audit", "0001_initial"),
        ("projects", "0001_initial"),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.CreateModel(
            name="DownloadEvent",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("target_type", models.CharField(max_length=80)),
                ("target_id", models.CharField(max_length=80)),
                ("filename", models.CharField(max_length=255)),
                ("checksum_sha256", models.CharField(max_length=64)),
                ("downloaded_at", models.DateTimeField(auto_now_add=True)),
                ("delivery_mode", models.CharField(choices=[("direct_response", "Direct response"), ("signed_url", "Signed URL")], default="direct_response", max_length=30)),
                ("actor", models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, to=settings.AUTH_USER_MODEL)),
                ("project", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="download_events", to="projects.researchproject")),
            ],
            options={"ordering": ["-downloaded_at"]},
        ),
    ]
