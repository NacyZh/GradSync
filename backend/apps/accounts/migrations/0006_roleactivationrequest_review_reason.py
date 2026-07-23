from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("accounts", "0005_collaboration_registration"),
    ]

    operations = [
        migrations.AddField(
            model_name="roleactivationrequest",
            name="review_reason",
            field=models.TextField(blank=True),
        ),
    ]
