from django.contrib.auth import get_user_model
from django.core.exceptions import PermissionDenied, ValidationError
from django.db import transaction
from django.db.models import Q
from django.utils import timezone

from apps.accounts.models import User
from apps.audit.models import AuditEvent
from apps.audit.services import record_event
from apps.notifications.models import Notification

from .access_services import project_capabilities
from .models import ProjectMembership, ProjectOwnershipTransfer, ResearchProject


def ensure_teacher_eligible(user):
    if not (
        user.global_role == User.GlobalRole.ADVISOR
        and user.status == User.Status.ACTIVE
        and user.active_role == User.RequestedRole.TEACHER
        and user.email_verified_at is not None
    ):
        raise ValidationError("Selected account is not an eligible teacher.")
    return user


def search_eligible_teachers(*, actor, query: str, project=None, limit: int = 25):
    if not getattr(actor, "is_authenticated", False):
        raise PermissionDenied
    query = str(query or "").strip()[:100]
    if len(query) < 2:
        return get_user_model().objects.none()
    queryset = (
        get_user_model()
        .objects.filter(
            global_role=User.GlobalRole.ADVISOR,
            status=User.Status.ACTIVE,
            active_role=User.RequestedRole.TEACHER,
            email_verified_at__isnull=False,
        )
        .filter(Q(email__icontains=query) | Q(name__icontains=query) | Q(nickname__icontains=query))
    )
    if project is not None:
        queryset = queryset.exclude(
            project_memberships__project=project,
            project_memberships__status=ProjectMembership.Status.ACTIVE,
        )
    return queryset.order_by("name", "email")[: max(1, min(limit, 25))]


def _require_collaborator_management(actor, project):
    if not project_capabilities(actor, project)["canManageCollaborators"]:
        raise PermissionDenied("Project collaborator management is forbidden.")
    if project.governance_state == ResearchProject.GovernanceState.HOLD:
        raise ValidationError("Project governance is on hold.")


def _notify(membership, actor, subject):
    Notification.objects.create(
        project=membership.project,
        recipient=membership.user,
        sender=actor,
        event_type=Notification.EventType.MEMBERSHIP_CHANGED,
        target_type="ProjectMembership",
        target_id=str(membership.id),
        subject=subject,
        action_path=f"/projects/{membership.project_id}",
        eligible_at=timezone.now(),
    )


@transaction.atomic
def assign_collaborator(*, actor, project, user, role, reason=""):
    project = ResearchProject.objects.select_for_update().get(pk=project.pk)
    _require_collaborator_management(actor, project)
    ensure_teacher_eligible(user)
    if role not in {
        ProjectMembership.Role.CO_ADVISOR,
        ProjectMembership.Role.REVIEWER,
        ProjectMembership.Role.OBSERVER,
    }:
        raise ValidationError("Select a supported collaborator role.")
    if actor.is_administrator and not str(reason).strip():
        raise ValidationError("Administrator interventions require a reason.")
    membership = (
        ProjectMembership.objects.select_for_update().filter(project=project, user=user).first()
    )
    if membership and membership.status == ProjectMembership.Status.ACTIVE:
        raise ValidationError("This teacher already has an active project role.")
    if membership:
        membership.role = role
        membership.status = ProjectMembership.Status.ACTIVE
        membership.removed_at = None
        membership.assigned_by = actor
        membership.assignment_reason = reason
        membership.role_changed_at = timezone.now()
        membership.version += 1
        membership.save()
    else:
        membership = ProjectMembership.objects.create(
            project=project,
            user=user,
            role=role,
            assigned_by=actor,
            assignment_reason=reason,
            role_changed_at=timezone.now(),
        )
    record_event(
        project,
        actor,
        "project_governance.collaborator_assigned",
        "Project collaborator assigned",
        membership,
        category=AuditEvent.Category.PROJECT_GOVERNANCE,
        target_snapshot={"role": role, "status": membership.status},
        allowed_snapshot_keys={"role", "status"},
    )
    _notify(membership, actor, "Project collaborator role assigned")
    return membership


@transaction.atomic
def change_collaborator_role(*, actor, membership, role, expected_version, reason=""):
    membership = (
        ProjectMembership.objects.select_for_update()
        .select_related("project", "user")
        .get(pk=membership.pk)
    )
    _require_collaborator_management(actor, membership.project)
    if membership.version != expected_version:
        raise ValidationError("The membership changed; refresh and try again.")
    if membership.role == ProjectMembership.Role.ADVISOR:
        raise ValidationError("Transfer ownership to change the primary advisor.")
    ensure_teacher_eligible(membership.user)
    if role not in {
        ProjectMembership.Role.CO_ADVISOR,
        ProjectMembership.Role.REVIEWER,
        ProjectMembership.Role.OBSERVER,
    }:
        raise ValidationError("Select a supported collaborator role.")
    if actor.is_administrator and not str(reason).strip():
        raise ValidationError("Administrator interventions require a reason.")
    membership.role = role
    membership.assignment_reason = reason
    membership.role_changed_at = timezone.now()
    membership.version += 1
    membership.save()
    record_event(
        membership.project,
        actor,
        "project_governance.collaborator_role_changed",
        "Project collaborator role changed",
        membership,
        category=AuditEvent.Category.PROJECT_GOVERNANCE,
        target_snapshot={"role": role, "version": membership.version},
        allowed_snapshot_keys={"role", "version"},
    )
    _notify(membership, actor, "Project collaborator role changed")
    return membership


@transaction.atomic
def remove_collaborator(*, actor, membership, expected_version, reason=""):
    membership = (
        ProjectMembership.objects.select_for_update()
        .select_related("project")
        .get(pk=membership.pk)
    )
    _require_collaborator_management(actor, membership.project)
    if membership.version != expected_version:
        raise ValidationError("The membership changed; refresh and try again.")
    if membership.role == ProjectMembership.Role.ADVISOR:
        raise ValidationError("The primary advisor must be transferred, not removed.")
    if actor.is_administrator and not str(reason).strip():
        raise ValidationError("Administrator interventions require a reason.")
    membership.status = ProjectMembership.Status.REMOVED
    membership.removed_at = timezone.now()
    membership.assignment_reason = reason
    membership.version += 1
    membership.save()
    record_event(
        membership.project,
        actor,
        "project_governance.collaborator_removed",
        "Project collaborator removed",
        membership,
        category=AuditEvent.Category.PROJECT_GOVERNANCE,
        target_snapshot={"status": membership.status, "version": membership.version},
        allowed_snapshot_keys={"status", "version"},
    )
    _notify(membership, actor, "Project collaborator role removed")
    return membership


@transaction.atomic
def transfer_ownership(
    *,
    actor,
    project,
    new_advisor,
    expected_version,
    previous_advisor_result=ProjectOwnershipTransfer.PreviousAdvisorResult.CO_ADVISOR,
    reason="",
    idempotency_key="",
):
    project = (
        ResearchProject.objects.select_for_update().select_related("advisor").get(pk=project.pk)
    )
    capabilities = project_capabilities(actor, project)
    if not capabilities["canTransferOwnership"] and not capabilities["canResolveGovernanceHold"]:
        raise PermissionDenied("Ownership transfer is forbidden.")
    if project.governance_version != expected_version:
        raise ValidationError("The project governance state changed; refresh and try again.")
    if actor.is_administrator and not str(reason).strip():
        raise ValidationError("Administrator interventions require a reason.")
    ensure_teacher_eligible(new_advisor)
    if new_advisor.pk == project.advisor_id:
        raise ValidationError("Select a different primary advisor.")
    if idempotency_key:
        existing = ProjectOwnershipTransfer.objects.filter(
            project=project, idempotency_key=idempotency_key
        ).first()
        if existing:
            return existing

    previous = project.advisor
    old_membership = (
        ProjectMembership.objects.select_for_update()
        .filter(project=project, user=previous, status=ProjectMembership.Status.ACTIVE)
        .first()
    )
    new_membership = (
        ProjectMembership.objects.select_for_update()
        .filter(project=project, user=new_advisor)
        .first()
    )
    ProjectMembership.objects.filter(
        project=project,
        role=ProjectMembership.Role.ADVISOR,
        status=ProjectMembership.Status.ACTIVE,
    ).update(
        role=previous_advisor_result
        if previous_advisor_result != ProjectOwnershipTransfer.PreviousAdvisorResult.REMOVED
        else ProjectMembership.Role.OBSERVER,
        status=ProjectMembership.Status.REMOVED
        if previous_advisor_result == ProjectOwnershipTransfer.PreviousAdvisorResult.REMOVED
        else ProjectMembership.Status.ACTIVE,
        role_changed_at=timezone.now(),
    )
    if old_membership:
        old_membership.refresh_from_db()
    if new_membership:
        new_membership.role = ProjectMembership.Role.ADVISOR
        new_membership.status = ProjectMembership.Status.ACTIVE
        new_membership.removed_at = None
        new_membership.assigned_by = actor
        new_membership.role_changed_at = timezone.now()
        new_membership.version += 1
        new_membership.save()
    else:
        new_membership = ProjectMembership.objects.create(
            project=project,
            user=new_advisor,
            role=ProjectMembership.Role.ADVISOR,
            assigned_by=actor,
            role_changed_at=timezone.now(),
        )
    project.advisor = new_advisor
    project.governance_state = ResearchProject.GovernanceState.NORMAL
    project.governance_hold_resolved_at = (
        timezone.now()
        if project.governance_hold_started_at
        else project.governance_hold_resolved_at
    )
    project.governance_hold_resolved_by = actor if actor.is_administrator else None
    project.governance_hold_resolution_reason = reason
    project.governance_hold_reason = ""
    project.governance_version += 1
    project.save()
    transfer = ProjectOwnershipTransfer.objects.create(
        project=project,
        previous_advisor=previous,
        new_advisor=new_advisor,
        previous_advisor_result=previous_advisor_result,
        initiated_by=actor,
        reason=reason,
        expected_project_version=expected_version,
        idempotency_key=idempotency_key,
    )
    record_event(
        project,
        actor,
        "project_governance.ownership_transferred",
        "Project ownership transferred",
        transfer,
        category=AuditEvent.Category.PROJECT_GOVERNANCE,
        target_snapshot={"governanceState": project.governance_state},
        allowed_snapshot_keys={"governanceState"},
    )
    _notify(new_membership, actor, "You are now the primary project advisor")
    return transfer


@transaction.atomic
def place_governance_hold(project, reason):
    project = ResearchProject.objects.select_for_update().get(pk=project.pk)
    if project.governance_state == ResearchProject.GovernanceState.HOLD:
        return project
    project.governance_state = ResearchProject.GovernanceState.HOLD
    project.governance_hold_reason = reason
    project.governance_hold_started_at = timezone.now()
    project.governance_version += 1
    project.save()
    return project
