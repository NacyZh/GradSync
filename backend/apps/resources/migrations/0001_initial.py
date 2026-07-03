import django.db.models.deletion
from django.conf import settings
from django.db import migrations, models


class Migration(migrations.Migration):
    initial = True

    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
        ("projects", "0001_initial"),
    ]

    operations = [
        migrations.CreateModel(
            name="ResourceType",
            fields=[
                (
                    "id",
                    models.BigAutoField(
                        auto_created=True, primary_key=True, serialize=False, verbose_name="ID"
                    ),
                ),
                ("name", models.CharField(max_length=255)),
                ("description", models.TextField(blank=True)),
                (
                    "scope",
                    models.CharField(
                        choices=[("global", "Global"), ("project", "Project")],
                        default="global",
                        max_length=20,
                    ),
                ),
                ("field_schema", models.JSONField(blank=True, default=list)),
                ("eligibility_policy", models.JSONField(blank=True, default=dict)),
                ("booking_policy", models.JSONField(blank=True, default=dict)),
                (
                    "status",
                    models.CharField(
                        choices=[("active", "Active"), ("archived", "Archived")],
                        default="active",
                        max_length=20,
                    ),
                ),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
            ],
            options={"ordering": ["name"]},
        ),
        migrations.CreateModel(
            name="ResourceItem",
            fields=[
                (
                    "id",
                    models.BigAutoField(
                        auto_created=True, primary_key=True, serialize=False, verbose_name="ID"
                    ),
                ),
                ("name", models.CharField(max_length=255)),
                ("description", models.TextField(blank=True)),
                ("location", models.CharField(blank=True, max_length=255)),
                ("field_values", models.JSONField(blank=True, default=dict)),
                ("availability_policy", models.JSONField(blank=True, default=dict)),
                (
                    "status",
                    models.CharField(
                        choices=[
                            ("available", "Available"),
                            ("unavailable", "Unavailable"),
                            ("retired", "Retired"),
                        ],
                        default="available",
                        max_length=20,
                    ),
                ),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                (
                    "resource_type",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.PROTECT,
                        related_name="items",
                        to="resources.resourcetype",
                    ),
                ),
            ],
            options={"ordering": ["name"]},
        ),
        migrations.CreateModel(
            name="Booking",
            fields=[
                (
                    "id",
                    models.BigAutoField(
                        auto_created=True, primary_key=True, serialize=False, verbose_name="ID"
                    ),
                ),
                ("starts_at", models.DateTimeField()),
                ("ends_at", models.DateTimeField()),
                (
                    "status",
                    models.CharField(
                        choices=[
                            ("reserved", "Reserved"),
                            ("cancelled", "Cancelled"),
                            ("completed", "Completed"),
                        ],
                        default="reserved",
                        max_length=20,
                    ),
                ),
                ("purpose", models.TextField(blank=True)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                ("cancelled_at", models.DateTimeField(blank=True, null=True)),
                (
                    "project",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="bookings",
                        to="projects.researchproject",
                    ),
                ),
                (
                    "requested_by",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.PROTECT,
                        to=settings.AUTH_USER_MODEL,
                    ),
                ),
                (
                    "resource_item",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.PROTECT,
                        related_name="bookings",
                        to="resources.resourceitem",
                    ),
                ),
            ],
        ),
    ]
