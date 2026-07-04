import django.db.models.deletion
from django.conf import settings
from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("accounts", "0004_locale_preference"),
    ]

    operations = [
        migrations.AlterField(
            model_name="user",
            name="status",
            field=models.CharField(
                choices=[
                    ("invited", "Invited"),
                    ("pending_email_verification", "Pending email verification"),
                    ("pending_role_activation", "Pending role activation"),
                    ("active", "Active"),
                    ("suspended", "Suspended"),
                    ("archived", "Archived"),
                ],
                default="active",
                max_length=30,
            ),
        ),
        migrations.AddField(
            model_name="user",
            name="requested_role",
            field=models.CharField(
                choices=[
                    ("student", "Student"),
                    ("teacher", "Teacher"),
                    ("administrator", "Administrator"),
                    ("pending", "Pending"),
                ],
                default="student",
                max_length=30,
            ),
        ),
        migrations.AddField(
            model_name="user",
            name="active_role",
            field=models.CharField(
                choices=[
                    ("student", "Student"),
                    ("teacher", "Teacher"),
                    ("administrator", "Administrator"),
                    ("pending", "Pending"),
                ],
                default="student",
                max_length=30,
            ),
        ),
        migrations.AddField(
            model_name="user",
            name="nickname",
            field=models.CharField(blank=True, max_length=80),
        ),
        migrations.AddField(
            model_name="user",
            name="email_verified_at",
            field=models.DateTimeField(blank=True, null=True),
        ),
        migrations.CreateModel(
            name="StudentProfile",
            fields=[
                (
                    "id",
                    models.BigAutoField(
                        auto_created=True, primary_key=True, serialize=False, verbose_name="ID"
                    ),
                ),
                (
                    "degree_type",
                    models.CharField(
                        choices=[("masters", "Masters"), ("doctoral", "Doctoral")], max_length=20
                    ),
                ),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                (
                    "user",
                    models.OneToOneField(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="student_profile",
                        to=settings.AUTH_USER_MODEL,
                    ),
                ),
            ],
        ),
        migrations.CreateModel(
            name="TeacherProfile",
            fields=[
                (
                    "id",
                    models.BigAutoField(
                        auto_created=True, primary_key=True, serialize=False, verbose_name="ID"
                    ),
                ),
                ("approved_at", models.DateTimeField()),
                (
                    "approved_by",
                    models.ForeignKey(
                        blank=True,
                        null=True,
                        on_delete=django.db.models.deletion.SET_NULL,
                        related_name="approved_teacher_profiles",
                        to=settings.AUTH_USER_MODEL,
                    ),
                ),
                (
                    "user",
                    models.OneToOneField(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="teacher_profile",
                        to=settings.AUTH_USER_MODEL,
                    ),
                ),
            ],
        ),
        migrations.CreateModel(
            name="EmailVerificationCode",
            fields=[
                (
                    "id",
                    models.BigAutoField(
                        auto_created=True, primary_key=True, serialize=False, verbose_name="ID"
                    ),
                ),
                ("email", models.EmailField(db_index=True, max_length=254)),
                (
                    "purpose",
                    models.CharField(
                        choices=[
                            ("registration", "Registration"),
                            ("email_change", "Email change"),
                        ],
                        default="registration",
                        max_length=30,
                    ),
                ),
                ("code_hash", models.CharField(max_length=128)),
                ("plain_code", models.CharField(blank=True, max_length=12)),
                (
                    "status",
                    models.CharField(
                        choices=[
                            ("pending", "Pending"),
                            ("consumed", "Consumed"),
                            ("expired", "Expired"),
                            ("revoked", "Revoked"),
                        ],
                        default="pending",
                        max_length=20,
                    ),
                ),
                ("expires_at", models.DateTimeField()),
                ("consumed_at", models.DateTimeField(blank=True, null=True)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
            ],
        ),
        migrations.CreateModel(
            name="RoleActivationRequest",
            fields=[
                (
                    "id",
                    models.BigAutoField(
                        auto_created=True, primary_key=True, serialize=False, verbose_name="ID"
                    ),
                ),
                (
                    "requested_role",
                    models.CharField(
                        choices=[("teacher", "Teacher"), ("administrator", "Administrator")],
                        max_length=30,
                    ),
                ),
                (
                    "activation_source",
                    models.CharField(
                        choices=[
                            ("administrator_approval", "Administrator approval"),
                            ("invitation", "Invitation"),
                        ],
                        default="administrator_approval",
                        max_length=40,
                    ),
                ),
                (
                    "status",
                    models.CharField(
                        choices=[
                            ("pending", "Pending"),
                            ("approved", "Approved"),
                            ("rejected", "Rejected"),
                            ("expired", "Expired"),
                            ("revoked", "Revoked"),
                        ],
                        default="pending",
                        max_length=20,
                    ),
                ),
                ("invitation_token_hash", models.CharField(blank=True, max_length=128)),
                ("expires_at", models.DateTimeField(blank=True, null=True)),
                ("reviewed_at", models.DateTimeField(blank=True, null=True)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                (
                    "reviewer",
                    models.ForeignKey(
                        blank=True,
                        null=True,
                        on_delete=django.db.models.deletion.SET_NULL,
                        related_name="reviewed_role_activation_requests",
                        to=settings.AUTH_USER_MODEL,
                    ),
                ),
                (
                    "user",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="role_activation_requests",
                        to=settings.AUTH_USER_MODEL,
                    ),
                ),
            ],
            options={"ordering": ["-created_at"]},
        ),
    ]
