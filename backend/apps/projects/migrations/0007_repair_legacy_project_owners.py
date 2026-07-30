from django.db import migrations
from django.utils import timezone


def repair_legacy_project_owners(apps, schema_editor):
    User = apps.get_model("accounts", "User")
    TeacherProfile = apps.get_model("accounts", "TeacherProfile")
    Project = apps.get_model("projects", "ResearchProject")
    Membership = apps.get_model("projects", "ProjectMembership")
    now = timezone.now()

    projects = Project.objects.select_related("advisor").filter(
        governance_state="hold",
        governance_hold_reason="owner_ineligible",
        advisor__global_role="advisor",
        advisor__status="active",
    )
    for project in projects.iterator():
        owner = project.advisor
        conflicting_primary = Membership.objects.filter(
            project=project,
            role="advisor",
            status="active",
        ).exclude(user=owner)
        if conflicting_primary.exists():
            continue

        User.objects.filter(pk=owner.pk).update(
            requested_role="teacher",
            active_role="teacher",
            email_verified_at=owner.email_verified_at or now,
        )
        TeacherProfile.objects.get_or_create(
            user_id=owner.pk,
            defaults={"approved_at": now, "approved_by_id": None},
        )

        membership = (
            Membership.objects.filter(project=project, user=owner, status="active").first()
            or Membership.objects.filter(project=project, user=owner).order_by("-id").first()
        )
        if membership is None:
            Membership.objects.create(
                project=project,
                user=owner,
                role="advisor",
                status="active",
                role_changed_at=now,
            )
        else:
            membership.role = "advisor"
            membership.status = "active"
            membership.removed_at = None
            membership.role_changed_at = now
            membership.version += 1
            membership.save(
                update_fields=[
                    "role",
                    "status",
                    "removed_at",
                    "role_changed_at",
                    "version",
                ]
            )

        project.governance_state = "normal"
        project.governance_hold_reason = ""
        project.governance_hold_resolved_at = now
        project.governance_hold_resolution_reason = (
            "Repaired legacy advisor role defaults introduced during access governance migration."
        )
        project.governance_version += 1
        project.save(
            update_fields=[
                "governance_state",
                "governance_hold_reason",
                "governance_hold_resolved_at",
                "governance_hold_resolution_reason",
                "governance_version",
                "updated_at",
            ]
        )


class Migration(migrations.Migration):
    dependencies = [
        ("accounts", "0007_access_security_lifecycle"),
        ("projects", "0006_project_closeout_record"),
    ]

    operations = [
        migrations.RunPython(repair_legacy_project_owners, migrations.RunPython.noop),
    ]
