from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("notifications", "0003_alter_notification_event_type"),
    ]

    operations = [
        migrations.AlterField(
            model_name="notification",
            name="event_type",
            field=models.CharField(
                choices=[
                    ("new_submission", "New submission"),
                    ("pending_review", "Pending review"),
                    ("approaching_deadline", "Approaching deadline"),
                    ("booking_changed", "Booking changed"),
                    ("teacher_feedback", "Teacher feedback"),
                    ("membership_changed", "Membership changed"),
                ],
                max_length=40,
            ),
        ),
    ]
