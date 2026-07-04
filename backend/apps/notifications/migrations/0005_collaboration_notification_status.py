import django.db.models.deletion
from django.db import migrations, models


def backfill_recipient_email(apps, schema_editor):
    Notification = apps.get_model("notifications", "Notification")
    for notification in Notification.objects.select_related("recipient").iterator():
        email = getattr(notification.recipient, "email", "") or ""
        if email and notification.recipient_email != email:
            notification.recipient_email = email
            notification.save(update_fields=["recipient_email"])


class Migration(migrations.Migration):
    dependencies = [
        ("notifications", "0004_membership_changed_event_type"),
    ]

    operations = [
        migrations.AlterField(
            model_name="notification",
            name="event_type",
            field=models.CharField(
                choices=[
                    ("verification_code", "Verification code"),
                    ("role_activation", "Role activation"),
                    ("new_submission", "New submission"),
                    ("pending_review", "Pending review"),
                    ("approaching_deadline", "Approaching deadline"),
                    ("booking_changed", "Booking changed"),
                    ("teacher_feedback", "Teacher feedback"),
                    ("teacher_feedback_available", "Teacher feedback available"),
                    ("membership_changed", "Membership changed"),
                    ("resource_use_decision", "Resource use decision"),
                ],
                max_length=40,
            ),
        ),
        migrations.AlterField(
            model_name="notification",
            name="project",
            field=models.ForeignKey(
                blank=True,
                null=True,
                on_delete=django.db.models.deletion.CASCADE,
                related_name="notifications",
                to="projects.researchproject",
            ),
        ),
        migrations.AddField(
            model_name="notification",
            name="recipient_email",
            field=models.EmailField(blank=True, db_index=True, max_length=254),
        ),
        migrations.AddField(
            model_name="notification",
            name="last_attempt_at",
            field=models.DateTimeField(blank=True, null=True),
        ),
        migrations.AddField(
            model_name="notification",
            name="retry_count",
            field=models.PositiveIntegerField(default=0),
        ),
        migrations.AlterField(
            model_name="notification",
            name="status",
            field=models.CharField(
                choices=[
                    ("pending", "Pending"),
                    ("queued", "Queued"),
                    ("sent", "Sent"),
                    ("failed", "Failed"),
                    ("retry_needed", "Retry needed"),
                    ("skipped", "Skipped"),
                ],
                default="pending",
                max_length=20,
            ),
        ),
        migrations.RunPython(backfill_recipient_email, migrations.RunPython.noop),
        migrations.AddIndex(
            model_name="notification",
            index=models.Index(fields=["recipient", "status"], name="notificatio_recipie_9b7c1f_idx"),
        ),
        migrations.AddIndex(
            model_name="notification",
            index=models.Index(fields=["status", "eligible_at"], name="notificatio_status_44aaf4_idx"),
        ),
    ]
