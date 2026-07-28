from __future__ import annotations

from collections.abc import Iterable
from datetime import date, datetime, time
from urllib.parse import urlparse

from django.core.exceptions import PermissionDenied
from django.db import IntegrityError, models, transaction
from django.db.models import Max
from django.utils import timezone

from apps.audit.services import record_execution_event

from .access_services import project_capabilities
from .models import (
    Deliverable,
    DeliverableAssignee,
    DeliverableEvidence,
    DeliverableFinalDecision,
    DeliverableReviewerDesignation,
    DeliverableReviewRecommendation,
    DeliverableRevision,
    DeliverableTaskLink,
    Milestone,
    MilestoneOwner,
    ProjectMaterial,
    ProjectMembership,
    ResearchProject,
)

MANAGER_ROLES = {
    ProjectMembership.Role.ADVISOR,
    ProjectMembership.Role.CO_ADVISOR,
}
REVIEWER_ROLES = MANAGER_ROLES | {ProjectMembership.Role.REVIEWER}


def _create_revision_action(*, recipient, revision, subject, dedupe_suffix):
    from apps.notifications.models import Notification
    from apps.notifications.outcome_services import create_follow_up_notification

    create_follow_up_notification(
        recipient=recipient,
        sender=revision.submitted_by,
        project=revision.project,
        event_type=Notification.EventType.PENDING_REVIEW,
        target_type="DeliverableRevision",
        target_id=str(revision.pk),
        subject=subject,
        action_path=(
            f"/projects/{revision.project_id}/execution?deliverable="
            f"{revision.deliverable_id}"
        ),
        category=Notification.Category.DELIVERABLE,
        requirement_type=Notification.RequirementType.ACTION,
        delivery_policy=Notification.DeliveryPolicy.IN_APP,
        due_at=timezone.make_aware(
            datetime.combine(revision.deliverable.due_date, time.max),
            timezone.get_current_timezone(),
        ),
        dedupe_key=f"deliverable:{revision.pk}:{dedupe_suffix}",
    )


def _complete_revision_actions(revision, event):
    from apps.notifications.outcome_services import reconcile_notifications_for_event

    reconcile_notifications_for_event(
        project=revision.project,
        target_type="DeliverableRevision",
        target_id=str(revision.pk),
        event_type=event.event_type,
        event_id=str(event.pk),
    )


def _active_members(project, user_ids: Iterable[int]):
    requested = set(user_ids)
    members = {
        membership.user_id: membership
        for membership in ProjectMembership.objects.filter(
            project=project,
            user_id__in=requested,
            status=ProjectMembership.Status.ACTIVE,
        ).select_related("user")
    }
    if not requested or set(members) != requested:
        raise ValueError("Select at least one active project member.")
    return members


def _require_writable(project: ResearchProject):
    if (
        project.status != ResearchProject.Status.ACTIVE
        or project.governance_state != ResearchProject.GovernanceState.NORMAL
    ):
        raise PermissionDenied("Project execution is read-only.")


def _require_capability(actor, project, capability):
    _require_writable(project)
    if not project_capabilities(actor, project).get(capability):
        raise PermissionDenied("Project execution action is forbidden.")


@transaction.atomic
def create_milestone(
    *,
    actor,
    project: ResearchProject,
    title: str,
    description: str,
    target_date: date,
    owner_ids: Iterable[int],
):
    _require_capability(actor, project, "canManageMilestones")
    owners = _active_members(project, owner_ids)
    order = (
        Milestone.objects.filter(project=project).aggregate(value=Max("order"))["value"]
        or -1
    ) + 1
    milestone = Milestone.objects.create(
        project=project,
        title=title.strip(),
        description=description.strip(),
        target_date=target_date,
        order=order,
        created_by=actor,
    )
    MilestoneOwner.objects.bulk_create(
        [
            MilestoneOwner(milestone=milestone, user_id=user_id, assigned_by=actor)
            for user_id in owners
        ]
    )
    record_execution_event(
        project=project,
        actor=actor,
        action="milestone.created",
        target=milestone,
        state={"status": milestone.current_status, "version": milestone.version},
    )
    return milestone


@transaction.atomic
def update_milestone(
    *,
    actor,
    milestone: Milestone,
    expected_version: int,
    title: str | None = None,
    description: str | None = None,
    target_date: date | None = None,
    owner_ids: Iterable[int] | None = None,
):
    milestone = Milestone.objects.select_for_update().select_related("project").get(
        pk=milestone.pk
    )
    _require_capability(actor, milestone.project, "canManageMilestones")
    if milestone.version != expected_version:
        raise ValueError("The milestone changed; refresh and try again.")
    if milestone.archived_at:
        raise ValueError("Archived milestones cannot be edited.")
    if title is not None:
        milestone.title = title.strip()
    if description is not None:
        milestone.description = description.strip()
    if target_date is not None:
        milestone.target_date = target_date
    if owner_ids is not None:
        owners = _active_members(milestone.project, owner_ids)
        milestone.owners.exclude(user_id__in=owners).delete()
        for user_id in owners:
            MilestoneOwner.objects.get_or_create(
                milestone=milestone,
                user_id=user_id,
                defaults={"assigned_by": actor},
            )
    milestone.version += 1
    milestone.save()
    reconcile_milestone(milestone)
    record_execution_event(
        project=milestone.project,
        actor=actor,
        action="milestone.updated",
        target=milestone,
        state={"status": milestone.current_status, "version": milestone.version},
    )
    return milestone


@transaction.atomic
def reorder_milestones(*, actor, project: ResearchProject, milestone_ids: list[int]):
    _require_capability(actor, project, "canManageMilestones")
    rows = list(
        Milestone.objects.select_for_update()
        .filter(project=project, id__in=milestone_ids)
        .order_by("id")
    )
    if len(rows) != len(milestone_ids):
        raise ValueError("Every milestone must belong to this project.")
    by_id = {row.id: row for row in rows}
    offset = len(rows) + 1000
    Milestone.objects.filter(id__in=milestone_ids).update(order=models.F("order") + offset)
    for order, milestone_id in enumerate(milestone_ids):
        row = by_id[milestone_id]
        row.order = order
        row.version += 1
        row.save(update_fields=["order", "version", "updated_at"])
    return [by_id[item_id] for item_id in milestone_ids]


@transaction.atomic
def archive_milestone(*, actor, milestone: Milestone, expected_version: int):
    milestone = Milestone.objects.select_for_update().select_related("project").get(
        pk=milestone.pk
    )
    _require_capability(actor, milestone.project, "canManageMilestones")
    if milestone.version != expected_version:
        raise ValueError("The milestone changed; refresh and try again.")
    now = timezone.now()
    milestone.current_status = Milestone.Status.ARCHIVED
    milestone.archived_at = now
    milestone.completed_at = None
    milestone.version += 1
    milestone.save()
    milestone.deliverables.exclude(current_status=Deliverable.Status.ARCHIVED).update(
        current_status=Deliverable.Status.ARCHIVED,
        archived_at=now,
        version=models.F("version") + 1,
    )
    record_execution_event(
        project=milestone.project,
        actor=actor,
        action="milestone.archived",
        target=milestone,
        state={"status": milestone.current_status, "version": milestone.version},
    )
    return milestone


@transaction.atomic
def create_deliverable(
    *,
    actor,
    milestone: Milestone,
    title: str,
    description: str,
    acceptance_criteria: str,
    due_date: date,
    assignee_ids: Iterable[int],
    reviewer_ids: Iterable[int] = (),
    required: bool = True,
    reviewer_required: bool = False,
    task_ids: Iterable[int] = (),
):
    milestone = Milestone.objects.select_related("project").get(pk=milestone.pk)
    project = milestone.project
    _require_capability(actor, project, "canManageDeliverables")
    if milestone.archived_at:
        raise ValueError("Archived milestones cannot receive deliverables.")
    assignees = _active_members(project, assignee_ids)
    reviewers = _active_members(project, reviewer_ids) if reviewer_ids else {}
    if any(item.role not in REVIEWER_ROLES for item in reviewers.values()):
        raise ValueError("Reviewers must have an eligible teacher project role.")
    if reviewer_required and not reviewers:
        raise ValueError("At least one reviewer is required.")
    criteria = acceptance_criteria.strip()
    if not criteria:
        raise ValueError("Acceptance criteria are required.")
    order = (
        Deliverable.objects.filter(milestone=milestone).aggregate(value=Max("order"))[
            "value"
        ]
        or -1
    ) + 1
    deliverable = Deliverable.objects.create(
        project=project,
        milestone=milestone,
        title=title.strip(),
        description=description.strip(),
        acceptance_criteria=criteria,
        due_date=due_date,
        required=required,
        reviewer_required=reviewer_required,
        order=order,
        created_by=actor,
    )
    DeliverableAssignee.objects.bulk_create(
        [
            DeliverableAssignee(
                deliverable=deliverable, user_id=user_id, assigned_by=actor
            )
            for user_id in assignees
        ]
    )
    DeliverableReviewerDesignation.objects.bulk_create(
        [
            DeliverableReviewerDesignation(
                deliverable=deliverable, reviewer_id=user_id, designated_by=actor
            )
            for user_id in reviewers
        ]
    )
    if task_ids:
        from apps.tasks.models import Task

        tasks = list(Task.objects.filter(project=project, id__in=set(task_ids)))
        if len(tasks) != len(set(task_ids)):
            raise ValueError("Every linked task must belong to this project.")
        DeliverableTaskLink.objects.bulk_create(
            [
                DeliverableTaskLink(deliverable=deliverable, task=task, linked_by=actor)
                for task in tasks
            ]
        )
    record_execution_event(
        project=project,
        actor=actor,
        action="deliverable.created",
        target=deliverable,
        state={"status": deliverable.current_status, "version": deliverable.version},
    )
    return deliverable


@transaction.atomic
def update_deliverable(
    *,
    actor,
    deliverable: Deliverable,
    expected_version: int,
    planning: dict | None = None,
    progress_percent: int | None = None,
    work_status: str | None = None,
    blocker_summary: str | None = None,
):
    deliverable = Deliverable.objects.select_for_update().select_related(
        "project", "milestone"
    ).get(pk=deliverable.pk)
    _require_writable(deliverable.project)
    if deliverable.version != expected_version:
        raise ValueError("The deliverable changed; refresh and try again.")
    capabilities = project_capabilities(actor, deliverable.project)
    is_assignee = deliverable.assignees.filter(
        user=actor, removed_at__isnull=True
    ).exists()
    if planning:
        if not capabilities["canManageDeliverables"]:
            raise PermissionDenied("Deliverable planning is restricted to advisors.")
        for field in (
            "title",
            "description",
            "acceptance_criteria",
            "due_date",
            "required",
            "reviewer_required",
        ):
            if field in planning:
                setattr(deliverable, field, planning[field])
        if "assignee_ids" in planning:
            assignees = _active_members(deliverable.project, planning["assignee_ids"])
            deliverable.assignees.filter(removed_at__isnull=True).exclude(
                user_id__in=assignees
            ).update(removed_at=timezone.now())
            for user_id in assignees:
                if not deliverable.assignees.filter(
                    user_id=user_id, removed_at__isnull=True
                ).exists():
                    DeliverableAssignee.objects.create(
                        deliverable=deliverable,
                        user_id=user_id,
                        assigned_by=actor,
                    )
    if any(value is not None for value in (progress_percent, work_status, blocker_summary)):
        if not (capabilities["canManageDeliverables"] or is_assignee):
            raise PermissionDenied("Deliverable progress update is forbidden.")
        if progress_percent is not None:
            if not 0 <= progress_percent <= 100:
                raise ValueError("Progress must be between 0 and 100.")
            deliverable.progress_percent = progress_percent
        if work_status is not None:
            if work_status not in {
                Deliverable.Status.PLANNED,
                Deliverable.Status.IN_PROGRESS,
                Deliverable.Status.BLOCKED,
            }:
                raise ValueError("Select a valid work status.")
            deliverable.current_status = work_status
        if blocker_summary is not None:
            deliverable.blocker_summary = blocker_summary.strip()
        if (
            deliverable.current_status == Deliverable.Status.BLOCKED
            and not deliverable.blocker_summary
        ):
            raise ValueError("A blocker summary is required.")
    deliverable.version += 1
    deliverable.save()
    reconcile_milestone(deliverable.milestone)
    record_execution_event(
        project=deliverable.project,
        actor=actor,
        action="deliverable.updated",
        target=deliverable,
        state={"status": deliverable.current_status, "version": deliverable.version},
    )
    return deliverable


@transaction.atomic
def archive_deliverable(*, actor, deliverable: Deliverable, expected_version: int):
    deliverable = Deliverable.objects.select_for_update().select_related(
        "project", "milestone"
    ).get(pk=deliverable.pk)
    _require_capability(actor, deliverable.project, "canManageDeliverables")
    if deliverable.version != expected_version:
        raise ValueError("The deliverable changed; refresh and try again.")
    if (
        deliverable.required
        and deliverable.milestone.current_status == Milestone.Status.COMPLETED
    ):
        raise ValueError("Reopen the completed milestone before archiving required work.")
    deliverable.current_status = Deliverable.Status.ARCHIVED
    deliverable.archived_at = timezone.now()
    deliverable.version += 1
    deliverable.save()
    reconcile_milestone(deliverable.milestone)
    record_execution_event(
        project=deliverable.project,
        actor=actor,
        action="deliverable.archived",
        target=deliverable,
        state={"status": deliverable.current_status, "version": deliverable.version},
    )
    return deliverable


def _validate_evidence(actor, deliverable, item):
    supplied = [
        key
        for key in ("project_material_id", "task_id", "weekly_progress_report_id", "external_url")
        if item.get(key)
    ]
    if len(supplied) != 1:
        raise ValueError("Each evidence item must select exactly one source.")
    key = supplied[0]
    defaults = {
        "project": deliverable.project,
        "label_snapshot": str(item.get("label") or "Evidence")[:255],
        "added_by": actor,
    }
    if key == "external_url":
        url = str(item[key])
        parsed = urlparse(url)
        if parsed.scheme != "https" or not parsed.netloc or len(url) > 2048:
            raise ValueError("External evidence must use a valid HTTPS URL.")
        return {
            **defaults,
            "external_url": url,
            "source_type_snapshot": DeliverableEvidence.SourceType.URL,
            "source_id_snapshot": url,
        }
    if key == "project_material_id":
        source = ProjectMaterial.objects.filter(
            pk=item[key], source_project=deliverable.project
        ).first()
        source_type = DeliverableEvidence.SourceType.MATERIAL
        field = "project_material"
    elif key == "task_id":
        from apps.tasks.models import Task

        source = Task.objects.filter(pk=item[key], project=deliverable.project).first()
        source_type = DeliverableEvidence.SourceType.TASK
        field = "task"
    else:
        from apps.submissions.models import WeeklyProgressReport

        source = WeeklyProgressReport.objects.filter(
            pk=item[key], project=deliverable.project
        ).first()
        source_type = DeliverableEvidence.SourceType.REPORT
        field = "weekly_progress_report"
    if source is None:
        raise ValueError("Evidence must belong to this project.")
    return {
        **defaults,
        field: source,
        "source_type_snapshot": source_type,
        "source_id_snapshot": str(source.pk),
    }


@transaction.atomic
def submit_deliverable(
    *,
    actor,
    deliverable: Deliverable,
    description: str,
    evidence: list[dict],
    idempotency_key: str = "",
):
    deliverable = Deliverable.objects.select_for_update().select_related(
        "project", "milestone"
    ).get(pk=deliverable.pk)
    _require_writable(deliverable.project)
    existing = None
    if idempotency_key:
        existing = deliverable.revisions.filter(idempotency_key=idempotency_key).first()
    if existing:
        return existing
    is_assignee = deliverable.assignees.filter(
        user=actor, removed_at__isnull=True
    ).exists()
    can_manage = project_capabilities(actor, deliverable.project)[
        "canManageDeliverables"
    ]
    if not is_assignee and not can_manage:
        raise PermissionDenied("Only an assignee or advisor may submit this deliverable.")
    if deliverable.current_status in {
        Deliverable.Status.ACCEPTED,
        Deliverable.Status.ARCHIVED,
    }:
        raise ValueError("This deliverable cannot receive a new revision.")
    if not evidence:
        raise ValueError("At least one evidence item is required.")
    if deliverable.reviewer_required and not deliverable.reviewer_designations.filter(
        removed_at__isnull=True
    ).exists():
        raise ValueError("An active reviewer designation is required.")
    prepared_evidence = [
        _validate_evidence(actor, deliverable, item) for item in evidence
    ]
    next_number = (
        deliverable.revisions.aggregate(value=Max("revision_number"))["value"] or 0
    ) + 1
    revision = DeliverableRevision.objects.create(
        project=deliverable.project,
        deliverable=deliverable,
        revision_number=next_number,
        criteria_snapshot=deliverable.acceptance_criteria,
        description_snapshot=description.strip(),
        submitted_by=actor,
        idempotency_key=idempotency_key,
    )
    DeliverableEvidence.objects.bulk_create(
        [
            DeliverableEvidence(revision=revision, **item)
            for item in prepared_evidence
        ]
    )
    from apps.submissions.review_assignment_services import assign_reviewer

    for designation in deliverable.reviewer_designations.select_related(
        "reviewer"
    ).filter(removed_at__isnull=True):
        membership = ProjectMembership.objects.filter(
            project=deliverable.project,
            user=designation.reviewer,
            role=ProjectMembership.Role.REVIEWER,
            status=ProjectMembership.Status.ACTIVE,
        ).first()
        if membership:
            assign_reviewer(
                actor=deliverable.project.advisor,
                project=deliverable.project,
                reviewer_membership=membership,
                target=revision,
            )
    deliverable.current_revision = revision
    deliverable.current_status = (
        Deliverable.Status.UNDER_REVIEW
        if deliverable.reviewer_required
        else Deliverable.Status.SUBMITTED
    )
    deliverable.version += 1
    deliverable.save()
    reconcile_milestone(deliverable.milestone)
    record_execution_event(
        project=deliverable.project,
        actor=actor,
        action="deliverable.submitted",
        target=revision,
        state={"status": revision.state},
    )
    designated_reviewers = list(
        deliverable.reviewer_designations.filter(
            removed_at__isnull=True
        ).select_related("reviewer")
    )
    if designated_reviewers:
        for designation in designated_reviewers:
            transaction.on_commit(
                lambda designation=designation: _create_revision_action(
                    recipient=designation.reviewer,
                    revision=revision,
                    subject="Deliverable review required",
                    dedupe_suffix=f"reviewer:{designation.reviewer_id}",
                )
            )
    else:
        transaction.on_commit(
            lambda: _create_revision_action(
                recipient=deliverable.project.advisor,
                revision=revision,
                subject="Deliverable decision required",
                dedupe_suffix="advisor-decision",
            )
        )
    return revision


@transaction.atomic
def recommend_deliverable(*, actor, revision, recommendation: str, rationale: str):
    revision = DeliverableRevision.objects.select_for_update().select_related(
        "project", "deliverable"
    ).get(pk=revision.pk)
    designation = revision.deliverable.reviewer_designations.filter(
        reviewer=actor, removed_at__isnull=True
    ).first()
    membership = ProjectMembership.objects.filter(
        project=revision.project,
        user=actor,
        status=ProjectMembership.Status.ACTIVE,
        role__in=REVIEWER_ROLES,
    ).first()
    if not designation or not membership:
        raise PermissionDenied("A current reviewer designation is required.")
    if recommendation not in DeliverableReviewRecommendation.Recommendation.values:
        raise ValueError("Select a valid recommendation.")
    if not rationale.strip():
        raise ValueError("Recommendation rationale is required.")
    revision.recommendations.filter(
        reviewer=actor, superseded_at__isnull=True
    ).update(superseded_at=timezone.now())
    result = DeliverableReviewRecommendation.objects.create(
        project=revision.project,
        revision=revision,
        reviewer=actor,
        recommendation=recommendation,
        rationale=rationale.strip(),
        review_assignment=revision.review_assignments.filter(
            reviewer_membership__user=actor,
            status="active",
        ).first(),
    )
    revision.state = (
        DeliverableRevision.State.RECOMMENDED_ACCEPT
        if recommendation == DeliverableReviewRecommendation.Recommendation.ACCEPT
        else DeliverableRevision.State.RECOMMENDED_RETURN
    )
    revision.save(update_fields=["state"])
    event = record_execution_event(
        project=revision.project,
        actor=actor,
        action="deliverable.recommended",
        target=revision,
        state={"status": revision.state},
    )
    transaction.on_commit(lambda: _complete_revision_actions(revision, event))
    transaction.on_commit(
        lambda: _create_revision_action(
            recipient=revision.project.advisor,
            revision=revision,
            subject="Deliverable final decision required",
            dedupe_suffix="advisor-decision",
        )
    )
    return result


@transaction.atomic
def decide_deliverable(
    *,
    actor,
    revision,
    decision: str,
    rationale: str,
    idempotency_key: str = "",
):
    revision = DeliverableRevision.objects.select_for_update().select_related(
        "project", "deliverable__milestone"
    ).get(pk=revision.pk)
    _require_capability(actor, revision.project, "canDecideDeliverables")
    if hasattr(revision, "final_decision"):
        return revision.final_decision
    if decision not in DeliverableFinalDecision.Decision.values:
        raise ValueError("Select a valid final decision.")
    if (
        decision == DeliverableFinalDecision.Decision.RETURNED
        and not rationale.strip()
    ):
        raise ValueError("A return rationale is required.")
    if (
        revision.deliverable.reviewer_required
        and not revision.recommendations.filter(superseded_at__isnull=True).exists()
    ):
        raise ValueError("A reviewer recommendation is required first.")
    try:
        result = DeliverableFinalDecision.objects.create(
            project=revision.project,
            revision=revision,
            decision=decision,
            rationale=rationale.strip(),
            decided_by=actor,
            idempotency_key=idempotency_key,
        )
    except IntegrityError:
        if idempotency_key:
            return DeliverableFinalDecision.objects.get(
                project=revision.project, idempotency_key=idempotency_key
            )
        raise
    deliverable = revision.deliverable
    now = timezone.now()
    if decision == DeliverableFinalDecision.Decision.ACCEPTED:
        revision.state = DeliverableRevision.State.ACCEPTED
        deliverable.current_status = Deliverable.Status.ACCEPTED
        deliverable.accepted_revision = revision
        deliverable.accepted_at = now
        deliverable.progress_percent = 100
    else:
        revision.state = DeliverableRevision.State.RETURNED
        deliverable.current_status = Deliverable.Status.CHANGES_REQUESTED
        deliverable.accepted_revision = None
        deliverable.accepted_at = None
    revision.save(update_fields=["state"])
    deliverable.version += 1
    deliverable.save()
    reconcile_milestone(deliverable.milestone)
    event = record_execution_event(
        project=revision.project,
        actor=actor,
        action="deliverable.decided",
        target=result,
        state={"status": decision},
        privileged=True,
    )
    transaction.on_commit(lambda: _complete_revision_actions(revision, event))
    return result


@transaction.atomic
def reconcile_milestone(milestone: Milestone):
    milestone = Milestone.objects.select_for_update().get(pk=milestone.pk)
    if milestone.archived_at:
        status = Milestone.Status.ARCHIVED
    else:
        required = list(milestone.deliverables.filter(required=True, archived_at__isnull=True))
        if required and all(
            item.current_status == Deliverable.Status.ACCEPTED for item in required
        ):
            status = Milestone.Status.COMPLETED
        elif any(item.current_status == Deliverable.Status.BLOCKED for item in required):
            status = Milestone.Status.BLOCKED
        elif milestone.target_date < timezone.localdate():
            status = Milestone.Status.OVERDUE
        elif any(
            item.current_status
            in {
                Deliverable.Status.IN_PROGRESS,
                Deliverable.Status.SUBMITTED,
                Deliverable.Status.UNDER_REVIEW,
                Deliverable.Status.CHANGES_REQUESTED,
            }
            for item in required
        ):
            status = Milestone.Status.IN_PROGRESS
        else:
            status = Milestone.Status.PLANNED
    changed = milestone.current_status != status
    milestone.current_status = status
    milestone.completed_at = (
        milestone.completed_at or timezone.now()
        if status == Milestone.Status.COMPLETED
        else None
    )
    if changed:
        milestone.version += 1
    milestone.save(
        update_fields=["current_status", "completed_at", "version", "updated_at"]
    )
    return milestone
