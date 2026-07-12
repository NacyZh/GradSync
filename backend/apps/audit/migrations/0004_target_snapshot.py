from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [("audit", "0003_audit_event_project_nullable")]

    operations = [
        migrations.AddField(
            model_name="auditevent",
            name="target_snapshot",
            field=models.JSONField(blank=True, default=dict),
        )
    ]
