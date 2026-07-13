from django.db import migrations, models


def backfill_booking_origin(apps, schema_editor):
    Booking = apps.get_model("resources", "Booking")
    Booking.objects.filter(origin="").update(origin="legacy_booking")


class Migration(migrations.Migration):
    dependencies = [("resources", "0004_standalone_quantity_bookings")]

    operations = [
        migrations.AddField(
            model_name="booking",
            name="origin",
            field=models.CharField(
                choices=[
                    ("student_request", "Student request"),
                    ("staff_direct", "Staff direct"),
                    ("legacy_booking", "Legacy booking"),
                ],
                default="legacy_booking",
                max_length=24,
            ),
        ),
        migrations.AddField(
            model_name="booking",
            name="completed_at",
            field=models.DateTimeField(blank=True, null=True),
        ),
        migrations.AddIndex(
            model_name="booking",
            index=models.Index(fields=["status", "created_at"], name="booking_review_queue_idx"),
        ),
        migrations.RunPython(backfill_booking_origin, migrations.RunPython.noop),
    ]
