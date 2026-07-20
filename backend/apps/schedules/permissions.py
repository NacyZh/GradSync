from django.contrib.auth import get_user_model
from django.db.models import Q, QuerySet
from django.utils import timezone

from apps.projects.models import ProjectMembership
from apps.projects.services import can_manage_project

from .models import ScheduleItem


def is_active_account(user) -> bool:
    return bool(
        user
        and getattr(user, "is_authenticated", False)
        and getattr(user, "status", None) == "active"
    )


def can_view_schedule_item(user, item: ScheduleItem, *, occurrence_at=None) -> bool:
    if not is_active_account(user):
        return False
    if item.scope == ScheduleItem.Scope.PERSONAL:
        return item.owner_id == user.id
    grant_time = occurrence_at or timezone.now()
    grants = item.recipient_grants.filter(recipient=user, valid_from__lte=grant_time)
    grants = grants.filter(Q(valid_until__isnull=True) | Q(valid_until__gt=grant_time))
    return item.owner_id == user.id or grants.exists() or can_manage_group_item(user, item)


def can_manage_group_item(user, item: ScheduleItem) -> bool:
    return bool(
        is_active_account(user)
        and item.scope == ScheduleItem.Scope.GROUP
        and (item.owner_id == user.id or getattr(user, "is_administrator", False))
    )


def can_publish_group_item(user) -> bool:
    return bool(is_active_account(user) and getattr(user, "is_advisor", False))


def eligible_recipient_accounts(user) -> QuerySet:
    users = get_user_model().objects.filter(status="active")
    if getattr(user, "is_administrator", False):
        return users
    if getattr(user, "global_role", None) != "advisor":
        return users.none()
    managed_project_ids = ProjectMembership.objects.filter(
        user=user,
        role=ProjectMembership.Role.ADVISOR,
        status=ProjectMembership.Status.ACTIVE,
    ).values("project_id")
    return users.filter(
        project_memberships__project_id__in=managed_project_ids,
        project_memberships__status=ProjectMembership.Status.ACTIVE,
    ).distinct()


def can_manage_report_schedule(user, project) -> bool:
    return is_active_account(user) and can_manage_project(user, project)
