from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):
    dependencies = [
        ("audit", "0002_download_event"),
    ]

    operations = [
        migrations.AlterField(
            model_name="auditevent",
            name="project",
            field=models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.CASCADE, related_name="audit_events", to="projects.researchproject"),
        ),
    ]
