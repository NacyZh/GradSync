from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("submissions", "0004_migrate_standalone_writing_participants"),
    ]

    operations = [
        migrations.AlterUniqueTogether(
            name="weeklyprogressreport",
            unique_together=set(),
        ),
        migrations.AddField(
            model_name="weeklyprogressreport",
            name="revision_number",
            field=models.PositiveIntegerField(default=1),
        ),
        migrations.AlterUniqueTogether(
            name="weeklyprogressreport",
            unique_together={("project", "student", "report_week_start", "revision_number")},
        ),
        migrations.AlterModelOptions(
            name="weeklyprogressreport",
            options={"ordering": ["-report_week_start", "-revision_number"]},
        ),
    ]
