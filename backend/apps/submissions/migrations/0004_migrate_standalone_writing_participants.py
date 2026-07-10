from django.db import migrations


def forwards(apps, schema_editor):
    writing_project_model = apps.get_model("submissions", "WritingProject")
    participant_model = apps.get_model("submissions", "WritingParticipant")
    for writing_project in writing_project_model.objects.select_related(
        "student", "legacy_project", "project", "project__advisor"
    ):
        participant_model.objects.get_or_create(
            writing_project=writing_project,
            user=writing_project.student,
            status="active",
            defaults={"participant_role": "student_author"},
        )
        project = writing_project.legacy_project or writing_project.project
        if project and project.advisor_id:
            participant_model.objects.get_or_create(
                writing_project=writing_project,
                user_id=project.advisor_id,
                status="active",
                defaults={"participant_role": "bound_advisor"},
            )


def backwards(apps, schema_editor):
    participant_model = apps.get_model("submissions", "WritingParticipant")
    participant_model.objects.filter(
        participant_role__in=["student_author", "bound_advisor"],
        assigned_by__isnull=True,
    ).delete()


class Migration(migrations.Migration):
    dependencies = [
        ("submissions", "0003_standalone_writing_boundaries"),
    ]

    operations = [
        migrations.RunPython(forwards, backwards),
    ]
