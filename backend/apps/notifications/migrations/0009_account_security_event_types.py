from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [("notifications", "0008_alter_notification_delivery_policy")]

    operations = [
        migrations.AlterField(
            model_name="notification",
            name="event_type",
            field=models.CharField(
                choices=[
                    ("verification_code", "Verification code"),
                    ("password_recovery", "Password recovery"),
                    ("email_change_security", "Email change security"),
                    ("role_activation", "Role activation"),
                    ("new_submission", "New submission"),
                    ("pending_review", "Pending review"),
                    ("approaching_deadline", "Approaching deadline"),
                    ("booking_changed", "Booking changed"),
                    ("teacher_feedback", "Teacher feedback"),
                    ("teacher_feedback_available", "Teacher feedback available"),
                    ("membership_changed", "Membership changed"),
                    ("resource_use_decision", "Resource use decision"),
                    ("schedule_published", "Schedule published"),
                    ("schedule_changed", "Schedule changed"),
                    ("schedule_cancelled", "Schedule cancelled"),
                    ("schedule_recipient_removed", "Schedule recipient removed"),
                    ("schedule_reminder", "Schedule reminder"),
                ],
                max_length=40,
            ),
        )
    ]
