from django.core.exceptions import PermissionDenied, ValidationError
from django.db import transaction
from django.db.models import Q
from django.utils import timezone

from apps.projects.models import ProjectMembership, ResearchProject
from apps.projects.services import can_manage_project

from .models import ScheduleAudience, ScheduleItem, ScheduleRecipientGrant
from .permissions import can_publish_group_item, eligible_recipient_accounts


def searchable_projects(actor, query=""):
    projects = ResearchProject.objects.filter(status=ResearchProject.Status.ACTIVE)
    if not getattr(actor, "is_administrator", False):
        projects = projects.filter(
            memberships__user=actor,
            memberships__role=ProjectMembership.Role.ADVISOR,
            memberships__status=ProjectMembership.Status.ACTIVE,
        )
    if query:
        projects = projects.filter(title__icontains=query)
    return projects.distinct().order_by("title", "id")


def searchable_accounts(actor, query=""):
    accounts = eligible_recipient_accounts(actor)
    if query:
        accounts = accounts.filter(Q(name__icontains=query) | Q(email__icontains=query))
    return accounts.order_by("name", "id")


def audience_options(actor, option_type, query="", limit=20):
    if not can_publish_group_item(actor):
        raise PermissionDenied("Only advisors and administrators can select group audiences.")
    if option_type == "project":
        return [
            {
                "id": project.id,
                "type": "project",
                "label": project.title,
                "secondaryLabel": "Active research project",
                "role": None,
                "status": project.status,
                "eligible": True,
                "eligibilityScope": "active_account"
                if getattr(actor, "is_administrator", False)
                else "manageable_project_member",
            }
            for project in searchable_projects(actor, query)[:limit]
        ]
    if option_type == "account":
        return [
            {
                "id": account.id,
                "type": "account",
                "label": account.name,
                "secondaryLabel": account.email,
                "role": account.global_role,
                "status": account.status,
                "eligible": True,
                "eligibilityScope": "active_account"
                if getattr(actor, "is_administrator", False)
                else "manageable_project_member",
            }
            for account in searchable_accounts(actor, query)[:limit]
        ]
    raise ValidationError({"type": "Choose project or account."})


@transaction.atomic
def resolve_audience(*, actor, item, project_ids, account_ids, resolved_at=None):
    if not can_publish_group_item(actor):
        raise PermissionDenied("Only advisors and administrators can publish group schedules.")
    if item.scope != ScheduleItem.Scope.GROUP:
        raise ValidationError("Audience grants require a group schedule.")
    project_ids = list(dict.fromkeys(project_ids or []))
    account_ids = list(dict.fromkeys(account_ids or []))
    if not project_ids and not account_ids:
        raise ValidationError({"audience": "Select at least one project or account."})

    projects = list(ResearchProject.objects.filter(id__in=project_ids))
    if len(projects) != len(project_ids) or any(
        project.status != ResearchProject.Status.ACTIVE or not can_manage_project(actor, project)
        for project in projects
    ):
        raise ValidationError({"audience": "A selected project is no longer eligible."})
    eligible_accounts = list(eligible_recipient_accounts(actor).filter(id__in=account_ids))
    if len(eligible_accounts) != len(account_ids):
        raise ValidationError({"audience": "A selected account is no longer eligible."})

    item.audiences.all().delete()
    for project in projects:
        ScheduleAudience.objects.create(
            schedule_item=item,
            scope_type=ScheduleAudience.ScopeType.PROJECT,
            project=project,
            created_by=actor,
        )
    for account in eligible_accounts:
        ScheduleAudience.objects.create(
            schedule_item=item,
            scope_type=ScheduleAudience.ScopeType.ACCOUNT,
            account=account,
            created_by=actor,
        )

    evidence = {}
    memberships = ProjectMembership.objects.filter(
        project__in=projects, status=ProjectMembership.Status.ACTIVE
    ).select_related("user")
    for membership in memberships:
        if membership.user_id == actor.id:
            continue
        entry = evidence.setdefault(
            membership.user_id,
            {"user": membership.user, "types": set(), "projects": set()},
        )
        entry["types"].add("project")
        entry["projects"].add(membership.project_id)
    for account in eligible_accounts:
        if account.id == actor.id:
            continue
        entry = evidence.setdefault(
            account.id, {"user": account, "types": set(), "projects": set()}
        )
        entry["types"].add("account")

    now = resolved_at or timezone.now()
    for entry in evidence.values():
        grant, _ = ScheduleRecipientGrant.objects.get_or_create(
            schedule_item=item,
            recipient=entry["user"],
            valid_until__isnull=True,
            defaults={
                "valid_from": now,
                "source_types": sorted(entry["types"]),
                "source_project_ids": sorted(entry["projects"]),
            },
        )
        grant.source_types = sorted(entry["types"])
        grant.source_project_ids = sorted(entry["projects"])
        grant.save(update_fields=["source_types", "source_project_ids", "resolved_at"])

    return {
        "projectCount": len(projects),
        "accountCount": len(eligible_accounts),
        "resolvedRecipientCount": len(evidence),
    }


@transaction.atomic
def reresolve_audience(item, *, resolved_at=None):
    if item.scope != ScheduleItem.Scope.GROUP:
        return {"added": 0, "removed": 0, "active": 0}
    now = resolved_at or timezone.now()
    audiences = list(item.audiences.select_related("project", "account"))
    project_ids = [
        audience.project_id
        for audience in audiences
        if audience.scope_type == ScheduleAudience.ScopeType.PROJECT and audience.project_id
    ]
    account_ids = [
        audience.account_id
        for audience in audiences
        if audience.scope_type == ScheduleAudience.ScopeType.ACCOUNT
        and audience.account_id
        and audience.account.status == "active"
    ]
    evidence = {}
    memberships = ProjectMembership.objects.filter(
        project_id__in=project_ids,
        status=ProjectMembership.Status.ACTIVE,
        user__status="active",
    )
    for membership in memberships:
        if membership.user_id == item.owner_id:
            continue
        entry = evidence.setdefault(membership.user_id, {"types": set(), "projects": set()})
        entry["types"].add("project")
        entry["projects"].add(membership.project_id)
    for account_id in account_ids:
        if account_id == item.owner_id:
            continue
        entry = evidence.setdefault(account_id, {"types": set(), "projects": set()})
        entry["types"].add("account")

    open_grants = {
        grant.recipient_id: grant
        for grant in item.recipient_grants.select_for_update().filter(valid_until__isnull=True)
    }
    removed = []
    for recipient_id, grant in open_grants.items():
        if recipient_id not in evidence:
            grant.valid_until = max(now, grant.valid_from + timezone.timedelta(microseconds=1))
            grant.save(update_fields=["valid_until", "resolved_at"])
            removed.append(grant.recipient)
    added = 0
    for recipient_id, entry in evidence.items():
        grant = open_grants.get(recipient_id)
        if grant is None:
            ScheduleRecipientGrant.objects.create(
                schedule_item=item,
                recipient_id=recipient_id,
                valid_from=now,
                source_types=sorted(entry["types"]),
                source_project_ids=sorted(entry["projects"]),
            )
            added += 1
        else:
            grant.source_types = sorted(entry["types"])
            grant.source_project_ids = sorted(entry["projects"])
            grant.save(update_fields=["source_types", "source_project_ids", "resolved_at"])
    if removed:
        from .reminder_services import dispatch_group_event

        dispatch_group_event(item, actor=item.owner, event_type="removed", recipients=removed)
    return {"added": added, "removed": len(removed), "active": len(evidence)}
