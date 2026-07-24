import uuid

import django.db.models.deletion
import django.utils.timezone
from django.conf import settings
from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("accounts", "0006_roleactivationrequest_review_reason"),
        ("notifications", "0009_account_security_event_types"),
    ]

    operations = [
        migrations.CreateModel(
            name="AccountSession",
            fields=[
                (
                    "id",
                    models.UUIDField(
                        default=uuid.uuid4, editable=False, primary_key=True, serialize=False
                    ),
                ),
                (
                    "django_session_key_hash",
                    models.CharField(blank=True, max_length=64, null=True, unique=True),
                ),
                (
                    "status",
                    models.CharField(
                        choices=[
                            ("active", "Active"),
                            ("revoked", "Revoked"),
                            ("expired", "Expired"),
                        ],
                        default="active",
                        max_length=20,
                    ),
                ),
                ("device_label", models.CharField(default="Unknown device", max_length=120)),
                ("user_agent", models.CharField(blank=True, max_length=255)),
                ("initial_ip_hash", models.CharField(blank=True, max_length=64)),
                ("last_ip_hash", models.CharField(blank=True, max_length=64)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("last_seen_at", models.DateTimeField(default=django.utils.timezone.now)),
                ("expires_at", models.DateTimeField()),
                ("revoked_at", models.DateTimeField(blank=True, null=True)),
                ("revoke_reason", models.CharField(blank=True, max_length=255)),
                (
                    "revoked_by",
                    models.ForeignKey(
                        blank=True,
                        null=True,
                        on_delete=django.db.models.deletion.SET_NULL,
                        related_name="revoked_account_sessions",
                        to=settings.AUTH_USER_MODEL,
                    ),
                ),
                (
                    "user",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="account_sessions",
                        to=settings.AUTH_USER_MODEL,
                    ),
                ),
            ],
        ),
        migrations.CreateModel(
            name="AccountRecoveryRequest",
            fields=[
                (
                    "id",
                    models.UUIDField(
                        default=uuid.uuid4, editable=False, primary_key=True, serialize=False
                    ),
                ),
                ("token_hash", models.CharField(max_length=64, unique=True)),
                (
                    "status",
                    models.CharField(
                        choices=[
                            ("pending", "Pending"),
                            ("consumed", "Consumed"),
                            ("superseded", "Superseded"),
                            ("expired", "Expired"),
                            ("revoked", "Revoked"),
                        ],
                        default="pending",
                        max_length=20,
                    ),
                ),
                ("requested_email_snapshot", models.EmailField(max_length=254)),
                ("requested_ip_hash", models.CharField(blank=True, max_length=64)),
                ("requested_user_agent", models.CharField(blank=True, max_length=255)),
                ("expires_at", models.DateTimeField()),
                ("consumed_at", models.DateTimeField(blank=True, null=True)),
                ("superseded_at", models.DateTimeField(blank=True, null=True)),
                ("revoked_at", models.DateTimeField(blank=True, null=True)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                (
                    "delivery_notification",
                    models.ForeignKey(
                        blank=True,
                        null=True,
                        on_delete=django.db.models.deletion.SET_NULL,
                        related_name="recovery_requests",
                        to="notifications.notification",
                    ),
                ),
                (
                    "user",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.PROTECT,
                        related_name="recovery_requests",
                        to=settings.AUTH_USER_MODEL,
                    ),
                ),
            ],
        ),
        migrations.CreateModel(
            name="EmailChangeRequest",
            fields=[
                (
                    "id",
                    models.UUIDField(
                        default=uuid.uuid4, editable=False, primary_key=True, serialize=False
                    ),
                ),
                ("previous_email", models.EmailField(max_length=254)),
                ("new_email", models.EmailField(max_length=254)),
                ("verification_hash", models.CharField(max_length=64, unique=True)),
                (
                    "status",
                    models.CharField(
                        choices=[
                            ("pending", "Pending"),
                            ("verified", "Verified"),
                            ("cancelled", "Cancelled"),
                            ("superseded", "Superseded"),
                            ("expired", "Expired"),
                        ],
                        default="pending",
                        max_length=20,
                    ),
                ),
                ("expires_at", models.DateTimeField()),
                ("verified_at", models.DateTimeField(blank=True, null=True)),
                ("cancelled_at", models.DateTimeField(blank=True, null=True)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                (
                    "delivery_notification",
                    models.ForeignKey(
                        blank=True,
                        null=True,
                        on_delete=django.db.models.deletion.SET_NULL,
                        related_name="email_change_deliveries",
                        to="notifications.notification",
                    ),
                ),
                (
                    "security_notification",
                    models.ForeignKey(
                        blank=True,
                        null=True,
                        on_delete=django.db.models.deletion.SET_NULL,
                        related_name="email_change_security_notices",
                        to="notifications.notification",
                    ),
                ),
                (
                    "user",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.PROTECT,
                        related_name="email_change_requests",
                        to=settings.AUTH_USER_MODEL,
                    ),
                ),
            ],
        ),
        migrations.AddIndex(
            model_name="accountsession",
            index=models.Index(
                fields=["user", "status", "-last_seen_at"], name="account_session_user_idx"
            ),
        ),
        migrations.AddIndex(
            model_name="accountsession",
            index=models.Index(fields=["status", "expires_at"], name="account_session_expiry_idx"),
        ),
        migrations.AddIndex(
            model_name="accountrecoveryrequest",
            index=models.Index(
                fields=["user", "status", "-created_at"], name="account_recovery_user_idx"
            ),
        ),
        migrations.AddIndex(
            model_name="accountrecoveryrequest",
            index=models.Index(fields=["status", "expires_at"], name="account_recovery_expiry_idx"),
        ),
        migrations.AddConstraint(
            model_name="accountrecoveryrequest",
            constraint=models.UniqueConstraint(
                condition=models.Q(("status", "pending")),
                fields=("user",),
                name="unique_pending_account_recovery",
            ),
        ),
        migrations.AddIndex(
            model_name="emailchangerequest",
            index=models.Index(
                fields=["user", "status", "-created_at"], name="email_change_user_idx"
            ),
        ),
        migrations.AddIndex(
            model_name="emailchangerequest",
            index=models.Index(fields=["new_email", "status"], name="email_change_address_idx"),
        ),
        migrations.AddConstraint(
            model_name="emailchangerequest",
            constraint=models.UniqueConstraint(
                condition=models.Q(("status", "pending")),
                fields=("user",),
                name="unique_pending_email_change_user",
            ),
        ),
        migrations.AddConstraint(
            model_name="emailchangerequest",
            constraint=models.UniqueConstraint(
                condition=models.Q(("status", "pending")),
                fields=("new_email",),
                name="unique_pending_email_change_address",
            ),
        ),
        migrations.AddConstraint(
            model_name="emailchangerequest",
            constraint=models.CheckConstraint(
                condition=models.Q(("previous_email", models.F("new_email")), _negated=True),
                name="email_change_addresses_differ",
            ),
        ),
    ]
