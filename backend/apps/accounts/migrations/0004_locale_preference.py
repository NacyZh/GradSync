from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("accounts", "0003_alter_user_status"),
    ]

    operations = [
        migrations.AddField(
            model_name="user",
            name="locale",
            field=models.CharField(default="en", max_length=5),
        ),
    ]
