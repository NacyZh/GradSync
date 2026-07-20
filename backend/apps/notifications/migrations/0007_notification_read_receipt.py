import django.db.models.deletion
from django.conf import settings
from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
        ("notifications", "0006_notification_delivery_policy_and_more"),
    ]

    operations = [
        migrations.CreateModel(
            name="NotificationReadReceipt",
            fields=[
                (
                    "id",
                    models.BigAutoField(
                        auto_created=True,
                        primary_key=True,
                        serialize=False,
                        verbose_name="ID",
                    ),
                ),
                ("viewed_at", models.DateTimeField(auto_now_add=True)),
                (
                    "notification",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="read_receipts",
                        to="notifications.notification",
                    ),
                ),
                (
                    "viewer",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="notification_read_receipts",
                        to=settings.AUTH_USER_MODEL,
                    ),
                ),
            ],
            options={
                "indexes": [
                    models.Index(
                        fields=["viewer", "viewed_at"],
                        name="notificatio_viewer_10c532_idx",
                    )
                ],
                "constraints": [
                    models.UniqueConstraint(
                        fields=("notification", "viewer"),
                        name="unique_notification_viewer_receipt",
                    )
                ],
            },
        ),
    ]
