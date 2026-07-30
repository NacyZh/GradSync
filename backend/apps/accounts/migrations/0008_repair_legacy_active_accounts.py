from django.db import migrations
from django.utils import timezone


def repair_legacy_active_accounts(apps, schema_editor):
    User = apps.get_model("accounts", "User")
    TeacherProfile = apps.get_model("accounts", "TeacherProfile")
    now = timezone.now()
    legacy_accounts = User.objects.filter(
        status="active",
        email_verified_at__isnull=True,
    )

    advisor_ids = list(
        legacy_accounts.filter(global_role="advisor").values_list("id", flat=True)
    )
    if advisor_ids:
        User.objects.filter(id__in=advisor_ids).update(
            requested_role="teacher",
            active_role="teacher",
            email_verified_at=now,
        )
        existing_profile_ids = set(
            TeacherProfile.objects.filter(user_id__in=advisor_ids).values_list(
                "user_id", flat=True
            )
        )
        TeacherProfile.objects.bulk_create(
            [
                TeacherProfile(
                    user_id=user_id,
                    approved_at=now,
                    approved_by_id=None,
                )
                for user_id in advisor_ids
                if user_id not in existing_profile_ids
            ]
        )

    legacy_accounts.filter(global_role="student").update(
        requested_role="student",
        active_role="student",
        email_verified_at=now,
    )
    legacy_accounts.filter(global_role="admin").update(
        requested_role="administrator",
        active_role="administrator",
        email_verified_at=now,
    )


class Migration(migrations.Migration):
    dependencies = [
        ("accounts", "0007_access_security_lifecycle"),
    ]

    operations = [
        migrations.RunPython(repair_legacy_active_accounts, migrations.RunPython.noop),
    ]
