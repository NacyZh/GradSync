from django.core.exceptions import PermissionDenied, ValidationError
from django.db import transaction
from django.utils import timezone

from apps.audit.models import AuditEvent
from apps.audit.services import record_event
from apps.projects.access_services import project_capabilities
from apps.projects.models import ProjectMembership

from .models import SubmissionReviewAssignment


def _target_project(target):
    if hasattr(target, "project"):
        return target.project
    return target.writing_project.project


@transaction.atomic
def assign_reviewer(*, actor, project, reviewer_membership, target):
    if not project_capabilities(actor, project)["canAssignReviews"]:
        raise PermissionDenied("Review assignment is forbidden.")
    reviewer_membership = ProjectMembership.objects.select_for_update().get(
        pk=reviewer_membership.pk
    )
    if (
        reviewer_membership.project_id != project.id
        or reviewer_membership.role != ProjectMembership.Role.REVIEWER
        or reviewer_membership.status != ProjectMembership.Status.ACTIVE
    ):
        raise ValidationError("Select an active reviewer for this project.")
    if _target_project(target).id != project.id:
        raise ValidationError("The review target does not belong to this project.")
    fields = {
        "weekly_report": None,
        "writing_version": None,
        "draft_version": None,
    }
    model_name = target._meta.model_name
    fields[
        {
            "weeklyprogressreport": "weekly_report",
            "writingversion": "writing_version",
            "draftversion": "draft_version",
        }[model_name]
    ] = target
    assignment, _ = SubmissionReviewAssignment.objects.get_or_create(
        reviewer_membership=reviewer_membership,
        status=SubmissionReviewAssignment.Status.ACTIVE,
        **fields,
        defaults={"project": project, "assigned_by": actor},
    )
    record_event(
        project,
        actor,
        "submission_review.reviewer_assigned",
        "Reviewer assigned to submission",
        assignment,
        category=AuditEvent.Category.SUBMISSION_REVIEW,
        target_snapshot={"status": assignment.status},
        allowed_snapshot_keys={"status"},
    )
    return assignment


@transaction.atomic
def remove_review_assignment(*, actor, assignment, expected_version):
    assignment = SubmissionReviewAssignment.objects.select_for_update().select_related(
        "project"
    ).get(pk=assignment.pk)
    if not project_capabilities(actor, assignment.project)["canAssignReviews"]:
        raise PermissionDenied("Review assignment removal is forbidden.")
    if assignment.version != expected_version:
        raise ValidationError("The review assignment changed; refresh and try again.")
    if assignment.status == SubmissionReviewAssignment.Status.REMOVED:
        return assignment
    assignment.status = SubmissionReviewAssignment.Status.REMOVED
    assignment.removed_by = actor
    assignment.removed_at = timezone.now()
    assignment.version += 1
    assignment.save()
    record_event(
        assignment.project,
        actor,
        "submission_review.reviewer_removed",
        "Reviewer assignment removed",
        assignment,
        category=AuditEvent.Category.SUBMISSION_REVIEW,
        target_snapshot={"status": assignment.status},
        allowed_snapshot_keys={"status"},
    )
    return assignment


def reviewer_can_access_target(*, user, target) -> bool:
    project = _target_project(target)
    capabilities = project_capabilities(user, project)
    if capabilities["canManageProject"] or capabilities["canSuperviseGovernance"]:
        return True
    membership = ProjectMembership.objects.filter(
        project=project,
        user=user,
        role=ProjectMembership.Role.REVIEWER,
        status=ProjectMembership.Status.ACTIVE,
    ).first()
    if not membership:
        return False
    lookup = {
        "weeklyprogressreport": {"weekly_report": target},
        "writingversion": {"writing_version": target},
        "draftversion": {"draft_version": target},
    }[target._meta.model_name]
    return SubmissionReviewAssignment.objects.filter(
        reviewer_membership=membership,
        status=SubmissionReviewAssignment.Status.ACTIVE,
        **lookup,
    ).exists()
