import django.db.models.deletion
from django.conf import settings
from django.db import migrations, models


def _table_names(connection):
    return set(connection.introspection.table_names())


def _column_names(connection, table_name):
    with connection.cursor() as cursor:
        description = connection.introspection.get_table_description(cursor, table_name)
    return {column.name for column in description}


def _copy_legacy_lab_resources(apps, schema_editor):
    connection = schema_editor.connection
    tables = _table_names(connection)
    if "resources_labresource" not in tables or "resources_resourceitem" not in tables:
        return

    ResourceType = apps.get_model("resources", "ResourceType")
    ResourceItem = apps.get_model("resources", "ResourceItem")

    with connection.cursor() as cursor:
        cursor.execute(
            """
            SELECT id, name, resource_type, location, status, booking_policy, created_at, updated_at
            FROM resources_labresource
            """
        )
        legacy_resources = cursor.fetchall()

    type_by_key = {}
    for _, _, resource_type, *_ in legacy_resources:
        key = resource_type or "equipment"
        if key not in type_by_key:
            label = key.replace("_", " ").title()
            resource_type_obj, _ = ResourceType.objects.get_or_create(
                name=label,
                defaults={
                    "description": "",
                    "scope": "global",
                    "field_schema": [],
                    "eligibility_policy": {},
                    "booking_policy": {},
                    "status": "active",
                },
            )
            type_by_key[key] = resource_type_obj

    for (
        legacy_id,
        name,
        resource_type,
        location,
        status,
        booking_policy,
        created_at,
        updated_at,
    ) in legacy_resources:
        ResourceItem.objects.update_or_create(
            id=legacy_id,
            defaults={
                "resource_type": type_by_key[resource_type or "equipment"],
                "name": name,
                "description": "",
                "location": location or "",
                "field_values": {},
                "availability_policy": booking_policy or {},
                "status": status,
                "created_at": created_at,
                "updated_at": updated_at,
            },
        )


def _ensure_booking_resource_item_column(apps, schema_editor):
    connection = schema_editor.connection
    tables = _table_names(connection)
    if "resources_booking" not in tables:
        return

    columns = _column_names(connection, "resources_booking")
    if "resource_item_id" not in columns:
        with connection.cursor() as cursor:
            cursor.execute("ALTER TABLE resources_booking ADD COLUMN resource_item_id bigint NULL")

    columns = _column_names(connection, "resources_booking")
    if "resource_id" in columns:
        with connection.cursor() as cursor:
            cursor.execute(
                """
                UPDATE resources_booking
                SET resource_item_id = resource_id
                WHERE resource_item_id IS NULL
                """
            )


def ensure_current_resource_inventory_schema(apps, schema_editor):
    connection = schema_editor.connection
    tables = _table_names(connection)
    ResourceType = apps.get_model("resources", "ResourceType")
    ResourceItem = apps.get_model("resources", "ResourceItem")

    if ResourceType._meta.db_table not in tables:
        schema_editor.create_model(ResourceType)
        tables.add(ResourceType._meta.db_table)
    if ResourceItem._meta.db_table not in tables:
        schema_editor.create_model(ResourceItem)

    _copy_legacy_lab_resources(apps, schema_editor)
    _ensure_booking_resource_item_column(apps, schema_editor)


class Migration(migrations.Migration):
    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
        ("resources", "0001_initial"),
    ]

    operations = [
        migrations.RunPython(ensure_current_resource_inventory_schema, migrations.RunPython.noop),
        migrations.AddField(
            model_name="resourceitem",
            name="manager",
            field=models.ForeignKey(
                blank=True,
                null=True,
                on_delete=django.db.models.deletion.SET_NULL,
                related_name="managed_resources",
                to=settings.AUTH_USER_MODEL,
            ),
        ),
        migrations.AddField(
            model_name="resourceitem",
            name="use_instructions",
            field=models.TextField(blank=True),
        ),
        migrations.CreateModel(
            name="ResourceUseSubmission",
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
                (
                    "submission_type",
                    models.CharField(
                        choices=[("request", "Request"), ("use_record", "Use record")],
                        max_length=20,
                    ),
                ),
                ("details", models.TextField()),
                (
                    "status",
                    models.CharField(
                        choices=[
                            ("pending", "Pending"),
                            ("confirmed", "Confirmed"),
                            ("rejected", "Rejected"),
                        ],
                        default="pending",
                        max_length=20,
                    ),
                ),
                ("decision_note", models.TextField(blank=True)),
                ("submitted_at", models.DateTimeField(auto_now_add=True)),
                ("decided_at", models.DateTimeField(blank=True, null=True)),
                (
                    "resource_item",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.PROTECT,
                        related_name="use_submissions",
                        to="resources.resourceitem",
                    ),
                ),
                (
                    "reviewer",
                    models.ForeignKey(
                        blank=True,
                        null=True,
                        on_delete=django.db.models.deletion.SET_NULL,
                        related_name="reviewed_resource_use_submissions",
                        to=settings.AUTH_USER_MODEL,
                    ),
                ),
                (
                    "student",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.PROTECT,
                        related_name="resource_use_submissions",
                        to=settings.AUTH_USER_MODEL,
                    ),
                ),
            ],
            options={
                "ordering": ["-submitted_at"],
            },
        ),
        migrations.AddIndex(
            model_name="resourceusesubmission",
            index=models.Index(
                fields=["resource_item", "status"], name="resources_r_resourc_79e988_idx"
            ),
        ),
        migrations.AddIndex(
            model_name="resourceusesubmission",
            index=models.Index(fields=["student", "status"], name="resources_r_student_b3ebe2_idx"),
        ),
    ]
