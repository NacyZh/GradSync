from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [("audit", "0004_target_snapshot")]

    operations = [
        migrations.AddField(
            model_name="auditevent",
            name="actor_snapshot",
            field=models.JSONField(blank=True, default=dict),
        ),
        migrations.AddField(
            model_name="auditevent",
            name="category",
            field=models.CharField(
                choices=[
                    ("account_security", "Account security"),
                    ("account_governance", "Account governance"),
                    ("project_governance", "Project governance"),
                    ("submission_review", "Submission review"),
                    ("material", "Material"),
                    ("resource", "Resource"),
                    ("schedule", "Schedule"),
                    ("notification", "Notification"),
                    ("audit_access", "Audit access"),
                    ("release_governance", "Release governance"),
                    ("other", "Other"),
                ],
                default="other",
                max_length=40,
            ),
        ),
        migrations.AddField(
            model_name="auditevent",
            name="correlation_id",
            field=models.CharField(blank=True, db_index=True, max_length=64),
        ),
        migrations.AddField(
            model_name="auditevent",
            name="outcome",
            field=models.CharField(
                choices=[
                    ("succeeded", "Succeeded"),
                    ("denied", "Denied"),
                    ("failed", "Failed"),
                    ("queued", "Queued"),
                ],
                default="succeeded",
                max_length=20,
            ),
        ),
        migrations.AddField(
            model_name="auditevent",
            name="reason",
            field=models.TextField(blank=True),
        ),
        migrations.AddField(
            model_name="auditevent",
            name="redaction_version",
            field=models.PositiveSmallIntegerField(default=1),
        ),
        migrations.AddIndex(
            model_name="auditevent",
            index=models.Index(fields=["-created_at", "-id"], name="audit_event_cursor_idx"),
        ),
        migrations.AddIndex(
            model_name="auditevent",
            index=models.Index(fields=["category", "-created_at"], name="audit_event_category_idx"),
        ),
        migrations.AddIndex(
            model_name="auditevent",
            index=models.Index(fields=["outcome", "-created_at"], name="audit_event_outcome_idx"),
        ),
        migrations.AddIndex(
            model_name="auditevent",
            index=models.Index(fields=["actor", "-created_at"], name="audit_event_actor_idx"),
        ),
        migrations.AddIndex(
            model_name="auditevent",
            index=models.Index(fields=["project", "-created_at"], name="audit_event_project_idx"),
        ),
        migrations.AddIndex(
            model_name="auditevent",
            index=models.Index(
                fields=["target_type", "target_id", "-created_at"],
                name="audit_event_target_idx",
            ),
        ),
    ]
