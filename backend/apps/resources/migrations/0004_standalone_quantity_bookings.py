import django.db.models.deletion
from django.db import migrations, models


def backfill_confirmed(apps, schema_editor):
    Booking = apps.get_model("resources", "Booking")
    Booking.objects.filter(status="reserved").update(status="confirmed")


class Migration(migrations.Migration):
    dependencies = [("resources", "0003_shared_resource_inventory")]

    operations = [
        migrations.AlterField(
            model_name="booking",
            name="project",
            field=models.ForeignKey(
                blank=True,
                null=True,
                on_delete=django.db.models.deletion.SET_NULL,
                related_name="bookings",
                to="projects.researchproject",
            ),
        ),
        migrations.AddField(
            model_name="booking", name="quantity", field=models.PositiveIntegerField(default=1)
        ),
        migrations.AddField(
            model_name="booking",
            name="confirmation_policy",
            field=models.CharField(
                choices=[("immediate", "Immediate"), ("approval_required", "Approval required")],
                default="immediate",
                max_length=24,
            ),
        ),
        migrations.AddField(
            model_name="booking", name="decision_note", field=models.TextField(blank=True)
        ),
        migrations.AddField(
            model_name="booking",
            name="decided_at",
            field=models.DateTimeField(blank=True, null=True),
        ),
        migrations.AddField(
            model_name="booking",
            name="reviewer",
            field=models.ForeignKey(
                blank=True,
                null=True,
                on_delete=django.db.models.deletion.SET_NULL,
                related_name="reviewed_resource_bookings",
                to="accounts.user",
            ),
        ),
        migrations.AddField(
            model_name="booking", name="version", field=models.PositiveIntegerField(default=1)
        ),
        migrations.AlterField(
            model_name="booking",
            name="status",
            field=models.CharField(
                choices=[
                    ("pending", "Pending"),
                    ("confirmed", "Confirmed"),
                    ("reserved", "Reserved (legacy)"),
                    ("rejected", "Rejected"),
                    ("cancelled", "Cancelled"),
                    ("completed", "Completed"),
                ],
                default="confirmed",
                max_length=20,
            ),
        ),
        migrations.RunPython(backfill_confirmed, migrations.RunPython.noop),
        migrations.AddConstraint(
            model_name="booking",
            constraint=models.CheckConstraint(
                condition=models.Q(quantity__gte=1), name="booking_quantity_gte_1"
            ),
        ),
        migrations.AddConstraint(
            model_name="booking",
            constraint=models.CheckConstraint(
                condition=models.Q(ends_at__gt=models.F("starts_at")),
                name="booking_end_after_start",
            ),
        ),
        migrations.AddIndex(
            model_name="booking",
            index=models.Index(
                fields=["resource_item", "status", "starts_at", "ends_at"],
                name="booking_overlap_idx",
            ),
        ),
        migrations.AddIndex(
            model_name="booking",
            index=models.Index(fields=["requested_by", "status"], name="booking_requester_idx"),
        ),
    ]
