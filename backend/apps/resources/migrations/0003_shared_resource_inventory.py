from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [("resources", "0002_resource_use_submissions")]

    operations = [
        migrations.AddField(
            model_name="resourcetype",
            name="confirmation_policy",
            field=models.CharField(
                choices=[("immediate", "Immediate"), ("approval_required", "Approval required")],
                default="immediate",
                max_length=24,
            ),
        ),
        migrations.AddField(
            model_name="resourceitem",
            name="total_quantity",
            field=models.PositiveIntegerField(default=1),
        ),
        migrations.AddField(
            model_name="resourceitem",
            name="confirmation_policy_override",
            field=models.CharField(
                blank=True,
                choices=[("immediate", "Immediate"), ("approval_required", "Approval required")],
                max_length=24,
                null=True,
            ),
        ),
        migrations.AddField(
            model_name="resourceitem",
            name="version",
            field=models.PositiveIntegerField(default=1),
        ),
        migrations.AddConstraint(
            model_name="resourceitem",
            constraint=models.CheckConstraint(
                condition=models.Q(total_quantity__gte=1),
                name="resources_item_quantity_gte_1",
            ),
        ),
        migrations.AddIndex(
            model_name="resourceitem",
            index=models.Index(
                fields=["resource_type", "status"], name="resources_r_resourc_9d31f5_idx"
            ),
        ),
    ]
