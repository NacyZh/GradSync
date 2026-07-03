from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("notifications", "0002_notification_metadata"),
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
                ],
                max_length=40,
            ),
        ),
    ]
