from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("notifications", "0007_notification_read_receipt"),
    ]

    operations = [
        migrations.AlterField(
            model_name="notification",
            name="delivery_policy",
            field=models.CharField(
                choices=[
                    ("in_app", "In app"),
                    ("in_app_email", "In app and email"),
                    ("email_only", "Email only"),
                ],
                default="in_app_email",
                max_length=20,
            ),
        ),
    ]
