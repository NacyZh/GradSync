import uuid

from django.conf import settings
from django.db import models
from django.db.models import Q


class ResearchProject(models.Model):
    class Status(models.TextChoices):
        ACTIVE = "active", "Active"
        ARCHIVED = "archived", "Archived"

    class GovernanceState(models.TextChoices):
        NORMAL = "normal", "Normal"
        HOLD = "hold", "Hold"

    class GovernanceHoldReason(models.TextChoices):
        OWNER_INELIGIBLE = "owner_ineligible", "Owner ineligible"
        LEGACY_ADMIN_OWNER = "legacy_admin_owner", "Legacy administrator owner"
        MIGRATION_CONFLICT = "migration_conflict", "Migration conflict"
        MANUAL_CORRECTION = "manual_correction", "Manual correction"

    title = models.CharField(max_length=255)
    description = models.TextField(blank=True)
    advisor = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.PROTECT, related_name="advised_projects"
    )
    status = models.CharField(max_length=20, choices=Status.choices, default=Status.ACTIVE)
    starts_on = models.DateField(null=True, blank=True)
    ends_on = models.DateField(null=True, blank=True)
    archived_at = models.DateTimeField(null=True, blank=True)
    governance_state = models.CharField(
        max_length=20, choices=GovernanceState.choices, default=GovernanceState.NORMAL
    )
    governance_hold_reason = models.CharField(
        max_length=40, choices=GovernanceHoldReason.choices, blank=True
    )
    governance_hold_started_at = models.DateTimeField(null=True, blank=True)
    governance_hold_resolved_at = models.DateTimeField(null=True, blank=True)
    governance_hold_resolved_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="resolved_project_governance_holds",
    )
    governance_hold_resolution_reason = models.TextField(blank=True)
    governance_version = models.PositiveIntegerField(default=1)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["title"]

    def __str__(self) -> str:
        return self.title


class ProjectMembership(models.Model):
    class Role(models.TextChoices):
        ADVISOR = "advisor", "Advisor"
        CO_ADVISOR = "co_advisor", "Co-advisor"
        STUDENT = "student", "Student"
        REVIEWER = "reviewer", "Reviewer"
        OBSERVER = "observer", "Observer"

    class Status(models.TextChoices):
        ACTIVE = "active", "Active"
        REMOVED = "removed", "Removed"

    project = models.ForeignKey(
        ResearchProject, on_delete=models.CASCADE, related_name="memberships"
    )
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="project_memberships"
    )
    role = models.CharField(max_length=20, choices=Role.choices)
    status = models.CharField(max_length=20, choices=Status.choices, default=Status.ACTIVE)
    joined_at = models.DateTimeField(auto_now_add=True)
    removed_at = models.DateTimeField(null=True, blank=True)
    assigned_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="assigned_project_memberships",
    )
    assignment_reason = models.TextField(blank=True)
    role_changed_at = models.DateTimeField(null=True, blank=True)
    version = models.PositiveIntegerField(default=1)

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["project", "user"],
                condition=Q(status="active"),
                name="unique_active_project_membership",
            ),
            models.UniqueConstraint(
                fields=["project"],
                condition=Q(status="active", role="advisor"),
                name="unique_active_primary_advisor",
            ),
        ]
        indexes = [
            models.Index(fields=["project", "role", "status"], name="project_member_role_idx"),
            models.Index(fields=["user", "role", "status"], name="project_member_user_idx"),
        ]

    def __str__(self) -> str:
        return f"{self.user_id}:{self.project_id}:{self.role}"


class ProjectOwnershipTransfer(models.Model):
    class PreviousAdvisorResult(models.TextChoices):
        CO_ADVISOR = "co_advisor", "Co-advisor"
        REVIEWER = "reviewer", "Reviewer"
        OBSERVER = "observer", "Observer"
        REMOVED = "removed", "Removed"

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    project = models.ForeignKey(
        ResearchProject, on_delete=models.PROTECT, related_name="ownership_transfers"
    )
    previous_advisor = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name="outgoing_project_transfers",
    )
    new_advisor = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name="incoming_project_transfers",
    )
    previous_advisor_result = models.CharField(
        max_length=20,
        choices=PreviousAdvisorResult.choices,
        default=PreviousAdvisorResult.CO_ADVISOR,
    )
    initiated_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name="initiated_project_transfers",
    )
    reason = models.TextField(blank=True)
    expected_project_version = models.PositiveIntegerField()
    idempotency_key = models.CharField(max_length=100, blank=True)
    completed_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        constraints = [
            models.CheckConstraint(
                condition=~Q(previous_advisor=models.F("new_advisor")),
                name="project_transfer_advisors_differ",
            ),
            models.UniqueConstraint(
                fields=["project", "idempotency_key"],
                condition=~Q(idempotency_key=""),
                name="unique_project_transfer_idempotency",
            ),
        ]


class ProjectCloseoutRecord(models.Model):
    project = models.ForeignKey(
        ResearchProject,
        on_delete=models.PROTECT,
        related_name="closeout_records",
    )
    archive_version = models.PositiveIntegerField()
    checklist = models.JSONField(default=dict)
    dispositions = models.JSONField(default=dict)
    snapshot = models.JSONField(default=dict)
    notes = models.TextField(blank=True, max_length=4000)
    archived_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name="project_closeouts",
    )
    archived_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-archive_version"]
        constraints = [
            models.UniqueConstraint(
                fields=["project", "archive_version"],
                name="unique_project_closeout_version",
            )
        ]
        indexes = [
            models.Index(
                fields=["project", "-archived_at"],
                name="project_closeout_time_idx",
            )
        ]


class ProjectMaterial(models.Model):
    class MaterialType(models.TextChoices):
        PAPER = "paper", "Paper"
        DOCUMENT = "document", "Document"
        CODE = "code", "Code"

    class VisibilityState(models.TextChoices):
        PROJECT_ONLY = "project-only", "Project-only"
        GROUP_WIDE = "group-wide", "Group-wide"

    class ClassificationState(models.TextChoices):
        ACTIVE = "active", "Active"
        PENDING_REVIEW = "pending_review", "Pending review"
        ARCHIVED = "archived", "Archived"

    class ClassificationReason(models.TextChoices):
        PREVIOUS_FUNCTIONAL_AREA = "previous_functional_area", "Previous functional area"
        EXPLICIT_PROJECT_SPECIFIC = "explicit_project_specific", "Explicit project-specific"
        AMBIGUOUS_LEGACY = "ambiguous_legacy", "Ambiguous legacy"
        MANUAL_REVIEW = "manual_review", "Manual review"

    source_project = models.ForeignKey(
        ResearchProject, on_delete=models.CASCADE, related_name="materials"
    )
    material_type = models.CharField(max_length=20, choices=MaterialType.choices)
    backing_record_id = models.PositiveIntegerField()
    visibility_state = models.CharField(
        max_length=20,
        choices=VisibilityState.choices,
        default=VisibilityState.PROJECT_ONLY,
    )
    classification_state = models.CharField(
        max_length=20,
        choices=ClassificationState.choices,
        default=ClassificationState.ACTIVE,
    )
    classification_reason = models.CharField(
        max_length=40,
        choices=ClassificationReason.choices,
        default=ClassificationReason.EXPLICIT_PROJECT_SPECIFIC,
    )
    visibility_changed_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="project_material_visibility_changes",
    )
    visibility_changed_at = models.DateTimeField(null=True, blank=True)
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name="created_project_materials",
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        indexes = [
            models.Index(
                fields=[
                    "source_project",
                    "material_type",
                    "visibility_state",
                    "classification_state",
                ],
                name="projects_mat_scope_idx",
            ),
            models.Index(
                fields=["material_type", "visibility_state", "classification_state"],
                name="projects_mat_discovery_idx",
            ),
            models.Index(
                fields=["visibility_changed_by", "visibility_changed_at"],
                name="projects_mat_vis_actor_idx",
            ),
        ]


class Milestone(models.Model):
    class Status(models.TextChoices):
        PLANNED = "planned", "Planned"
        IN_PROGRESS = "in_progress", "In progress"
        AT_RISK = "at_risk", "At risk"
        BLOCKED = "blocked", "Blocked"
        OVERDUE = "overdue", "Overdue"
        COMPLETED = "completed", "Completed"
        ARCHIVED = "archived", "Archived"

    project = models.ForeignKey(
        ResearchProject, on_delete=models.CASCADE, related_name="milestones"
    )
    title = models.CharField(max_length=255)
    description = models.TextField(blank=True, max_length=8000)
    target_date = models.DateField()
    order = models.PositiveIntegerField()
    current_status = models.CharField(
        max_length=20, choices=Status.choices, default=Status.PLANNED
    )
    completed_at = models.DateTimeField(null=True, blank=True)
    archived_at = models.DateTimeField(null=True, blank=True)
    version = models.PositiveIntegerField(default=1)
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name="created_milestones",
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["order", "id"]
        constraints = [
            models.UniqueConstraint(
                fields=["project", "order"], name="unique_project_milestone_order"
            ),
            models.CheckConstraint(
                condition=Q(current_status="completed", completed_at__isnull=False)
                | (~Q(current_status="completed") & Q(completed_at__isnull=True)),
                name="milestone_completed_timestamp",
            ),
            models.CheckConstraint(
                condition=Q(current_status="archived", archived_at__isnull=False)
                | (~Q(current_status="archived") & Q(archived_at__isnull=True)),
                name="milestone_archived_timestamp",
            ),
        ]
        indexes = [
            models.Index(
                fields=["project", "current_status", "target_date", "order"],
                name="project_milestone_state_idx",
            ),
            models.Index(
                fields=["project", "archived_at", "order"],
                name="project_milestone_archive_idx",
            ),
        ]

    def reconcile_status(self):
        from .execution_services import reconcile_milestone

        return reconcile_milestone(self)


class MilestoneOwner(models.Model):
    milestone = models.ForeignKey(
        Milestone, on_delete=models.CASCADE, related_name="owners"
    )
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name="owned_milestones",
    )
    assigned_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name="assigned_milestone_owners",
    )
    assigned_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["milestone", "user"], name="unique_milestone_owner"
            )
        ]
        indexes = [
            models.Index(fields=["user", "milestone"], name="milestone_owner_user_idx")
        ]


class Deliverable(models.Model):
    class Status(models.TextChoices):
        PLANNED = "planned", "Planned"
        IN_PROGRESS = "in_progress", "In progress"
        BLOCKED = "blocked", "Blocked"
        SUBMITTED = "submitted", "Submitted"
        UNDER_REVIEW = "under_review", "Under review"
        CHANGES_REQUESTED = "changes_requested", "Changes requested"
        ACCEPTED = "accepted", "Accepted"
        ARCHIVED = "archived", "Archived"

    project = models.ForeignKey(
        ResearchProject, on_delete=models.CASCADE, related_name="deliverables"
    )
    milestone = models.ForeignKey(
        Milestone, on_delete=models.CASCADE, related_name="deliverables"
    )
    title = models.CharField(max_length=255)
    description = models.TextField(blank=True, max_length=8000)
    acceptance_criteria = models.TextField(max_length=8000)
    due_date = models.DateField()
    required = models.BooleanField(default=True)
    reviewer_required = models.BooleanField(default=False)
    order = models.PositiveIntegerField()
    current_status = models.CharField(
        max_length=24, choices=Status.choices, default=Status.PLANNED
    )
    progress_percent = models.PositiveSmallIntegerField(default=0)
    blocker_summary = models.TextField(blank=True, max_length=2000)
    current_revision = models.ForeignKey(
        "DeliverableRevision",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="+",
    )
    accepted_revision = models.ForeignKey(
        "DeliverableRevision",
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        related_name="+",
    )
    accepted_at = models.DateTimeField(null=True, blank=True)
    archived_at = models.DateTimeField(null=True, blank=True)
    version = models.PositiveIntegerField(default=1)
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name="created_deliverables",
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["milestone_id", "order", "id"]
        constraints = [
            models.UniqueConstraint(
                fields=["milestone", "order"], name="unique_milestone_deliverable_order"
            ),
            models.CheckConstraint(
                condition=Q(progress_percent__gte=0, progress_percent__lte=100),
                name="deliverable_progress_range",
            ),
        ]
        indexes = [
            models.Index(
                fields=["project", "current_status", "due_date"],
                name="deliverable_project_state_idx",
            ),
            models.Index(
                fields=["milestone", "required", "current_status"],
                name="deliverable_required_state_idx",
            ),
            models.Index(
                fields=["project", "archived_at", "updated_at"],
                name="deliverable_archive_idx",
            ),
        ]


class DeliverableAssignee(models.Model):
    deliverable = models.ForeignKey(
        Deliverable, on_delete=models.CASCADE, related_name="assignees"
    )
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name="deliverable_assignments",
    )
    assigned_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name="created_deliverable_assignments",
    )
    assigned_at = models.DateTimeField(auto_now_add=True)
    removed_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["deliverable", "user"],
                condition=Q(removed_at__isnull=True),
                name="unique_open_deliverable_assignee",
            )
        ]
        indexes = [
            models.Index(
                fields=["user", "removed_at", "deliverable"],
                name="deliverable_assignee_user_idx",
            ),
            models.Index(
                fields=["deliverable", "removed_at"],
                name="deliverable_assignee_open_idx",
            ),
        ]


class DeliverableReviewerDesignation(models.Model):
    deliverable = models.ForeignKey(
        Deliverable, on_delete=models.CASCADE, related_name="reviewer_designations"
    )
    reviewer = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name="designated_deliverable_reviews",
    )
    designated_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name="created_deliverable_reviewer_designations",
    )
    designated_at = models.DateTimeField(auto_now_add=True)
    removed_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["deliverable", "reviewer"],
                condition=Q(removed_at__isnull=True),
                name="unique_open_deliverable_reviewer",
            )
        ]
        indexes = [
            models.Index(
                fields=["deliverable", "removed_at"],
                name="deliverable_reviewer_open_idx",
            ),
            models.Index(
                fields=["reviewer", "removed_at", "deliverable"],
                name="deliverable_reviewer_user_idx",
            ),
        ]


class DeliverableTaskLink(models.Model):
    deliverable = models.ForeignKey(
        Deliverable, on_delete=models.CASCADE, related_name="task_links"
    )
    task = models.ForeignKey(
        "tasks.Task", on_delete=models.CASCADE, related_name="deliverable_links"
    )
    linked_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name="created_deliverable_task_links",
    )
    linked_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["deliverable", "task"], name="unique_deliverable_task_link"
            )
        ]
        indexes = [
            models.Index(fields=["task", "deliverable"], name="deliverable_task_idx"),
            models.Index(fields=["deliverable", "task"], name="deliverable_link_idx"),
        ]


class DeliverableRevision(models.Model):
    class State(models.TextChoices):
        SUBMITTED = "submitted", "Submitted"
        RECOMMENDED_ACCEPT = "recommended_accept", "Recommended accept"
        RECOMMENDED_RETURN = "recommended_return", "Recommended return"
        ACCEPTED = "accepted", "Accepted"
        RETURNED = "returned", "Returned"

    project = models.ForeignKey(
        ResearchProject, on_delete=models.CASCADE, related_name="deliverable_revisions"
    )
    deliverable = models.ForeignKey(
        Deliverable, on_delete=models.CASCADE, related_name="revisions"
    )
    revision_number = models.PositiveIntegerField()
    criteria_snapshot = models.TextField(max_length=8000)
    description_snapshot = models.TextField(max_length=8000)
    submitted_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name="submitted_deliverable_revisions",
    )
    submitted_at = models.DateTimeField(auto_now_add=True)
    idempotency_key = models.CharField(max_length=100, blank=True)
    state = models.CharField(
        max_length=24, choices=State.choices, default=State.SUBMITTED
    )

    class Meta:
        ordering = ["-revision_number"]
        constraints = [
            models.UniqueConstraint(
                fields=["deliverable", "revision_number"],
                name="unique_deliverable_revision_number",
            ),
            models.UniqueConstraint(
                fields=["deliverable", "idempotency_key"],
                condition=~Q(idempotency_key=""),
                name="unique_deliverable_revision_retry",
            ),
        ]
        indexes = [
            models.Index(
                fields=["deliverable", "-revision_number"],
                name="deliverable_revision_order_idx",
            ),
            models.Index(
                fields=["project", "state", "submitted_at"],
                name="deliverable_revision_state_idx",
            ),
        ]


class DeliverableEvidence(models.Model):
    class SourceType(models.TextChoices):
        MATERIAL = "project_material", "Project material"
        TASK = "task", "Task"
        REPORT = "weekly_progress_report", "Weekly progress report"
        URL = "external_url", "External URL"

    project = models.ForeignKey(
        ResearchProject, on_delete=models.CASCADE, related_name="deliverable_evidence"
    )
    revision = models.ForeignKey(
        DeliverableRevision, on_delete=models.CASCADE, related_name="evidence"
    )
    project_material = models.ForeignKey(
        ProjectMaterial,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="deliverable_evidence",
    )
    task = models.ForeignKey(
        "tasks.Task",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="deliverable_evidence",
    )
    weekly_progress_report = models.ForeignKey(
        "submissions.WeeklyProgressReport",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="deliverable_evidence",
    )
    external_url = models.URLField(max_length=2048, blank=True)
    label_snapshot = models.CharField(max_length=255)
    source_type_snapshot = models.CharField(max_length=32, choices=SourceType.choices)
    source_id_snapshot = models.CharField(max_length=255, blank=True)
    added_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name="added_deliverable_evidence",
    )
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        indexes = [
            models.Index(fields=["revision", "id"], name="deliverable_evidence_rev_idx"),
            models.Index(
                fields=["project_material", "revision"],
                name="deliverable_evidence_mat_idx",
            ),
            models.Index(fields=["task", "revision"], name="deliverable_evidence_task_idx"),
            models.Index(
                fields=["weekly_progress_report", "revision"],
                name="deliver_evidence_report_idx",
            ),
        ]


class DeliverableReviewRecommendation(models.Model):
    class Recommendation(models.TextChoices):
        ACCEPT = "accept", "Accept"
        RETURN = "return", "Return"

    project = models.ForeignKey(
        ResearchProject,
        on_delete=models.CASCADE,
        related_name="deliverable_recommendations",
    )
    revision = models.ForeignKey(
        DeliverableRevision, on_delete=models.CASCADE, related_name="recommendations"
    )
    reviewer = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name="deliverable_recommendations",
    )
    recommendation = models.CharField(max_length=10, choices=Recommendation.choices)
    rationale = models.TextField(max_length=8000)
    review_assignment = models.ForeignKey(
        "submissions.SubmissionReviewAssignment",
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        related_name="deliverable_recommendations",
    )
    created_at = models.DateTimeField(auto_now_add=True)
    superseded_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["revision", "reviewer"],
                condition=Q(superseded_at__isnull=True),
                name="unique_open_deliverable_recommendation",
            )
        ]
        indexes = [
            models.Index(
                fields=["revision", "superseded_at", "created_at"],
                name="deliver_recommend_rev_idx",
            ),
            models.Index(
                fields=["reviewer", "superseded_at", "created_at"],
                name="deliver_recommend_user_idx",
            ),
        ]


class DeliverableFinalDecision(models.Model):
    class Decision(models.TextChoices):
        ACCEPTED = "accepted", "Accepted"
        RETURNED = "returned", "Returned"

    project = models.ForeignKey(
        ResearchProject, on_delete=models.CASCADE, related_name="deliverable_decisions"
    )
    revision = models.OneToOneField(
        DeliverableRevision, on_delete=models.PROTECT, related_name="final_decision"
    )
    decision = models.CharField(max_length=10, choices=Decision.choices)
    rationale = models.TextField(blank=True, max_length=8000)
    decided_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name="deliverable_final_decisions",
    )
    decided_at = models.DateTimeField(auto_now_add=True)
    idempotency_key = models.CharField(max_length=100, blank=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["project", "idempotency_key"],
                condition=~Q(idempotency_key=""),
                name="unique_deliverable_decision_retry",
            )
        ]
        indexes = [
            models.Index(
                fields=["project", "decision", "decided_at"],
                name="deliver_decision_project_idx",
            ),
            models.Index(
                fields=["revision", "decided_at"],
                name="deliver_decision_rev_idx",
            ),
        ]


class DecisionRecord(models.Model):
    class Status(models.TextChoices):
        CURRENT = "current", "Current"
        SUPERSEDED = "superseded", "Superseded"

    project = models.ForeignKey(
        ResearchProject, on_delete=models.CASCADE, related_name="decisions"
    )
    title = models.CharField(max_length=255)
    context = models.TextField(max_length=8000)
    options_considered = models.JSONField(default=list)
    outcome = models.TextField(max_length=8000)
    rationale = models.TextField(max_length=8000)
    owner = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name="owned_project_decisions",
    )
    effective_date = models.DateField()
    status = models.CharField(
        max_length=16, choices=Status.choices, default=Status.CURRENT
    )
    supersedes = models.OneToOneField(
        "self",
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        related_name="superseded_by",
    )
    published_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name="published_project_decisions",
    )
    published_at = models.DateTimeField(auto_now_add=True)
    idempotency_key = models.CharField(max_length=100, blank=True)

    class Meta:
        ordering = ["-effective_date", "-id"]
        constraints = [
            models.UniqueConstraint(
                fields=["project", "idempotency_key"],
                condition=~Q(idempotency_key=""),
                name="unique_project_decision_retry",
            )
        ]
        indexes = [
            models.Index(
                fields=["project", "status", "effective_date"],
                name="project_decision_state_idx",
            ),
            models.Index(
                fields=["project", "owner", "status"],
                name="project_decision_owner_idx",
            ),
        ]

    def delete(self, *args, **kwargs):
        raise ValueError("Published decision records cannot be deleted.")


class RiskRecord(models.Model):
    class Level(models.TextChoices):
        LOW = "low", "Low"
        MEDIUM = "medium", "Medium"
        HIGH = "high", "High"

    class State(models.TextChoices):
        RAISED = "raised", "Raised"
        OPEN = "open", "Open"
        MITIGATING = "mitigating", "Mitigating"
        ACCEPTED = "accepted", "Accepted"
        RESOLVED = "resolved", "Resolved"

    class SourceType(models.TextChoices):
        MANUAL = "manual", "Manual"
        REPORT_BLOCKER = "report_blocker", "Report blocker"
        DELIVERABLE = "deliverable", "Deliverable"
        DECISION = "decision", "Decision"

    project = models.ForeignKey(
        ResearchProject, on_delete=models.CASCADE, related_name="risks"
    )
    title = models.CharField(max_length=255)
    description = models.TextField(max_length=8000)
    source_type = models.CharField(
        max_length=24, choices=SourceType.choices, default=SourceType.MANUAL
    )
    source_key = models.CharField(max_length=160, blank=True)
    likelihood = models.CharField(
        max_length=10, choices=Level.choices, default=Level.LOW
    )
    impact = models.CharField(
        max_length=10, choices=Level.choices, default=Level.LOW
    )
    severity = models.CharField(
        max_length=10, choices=Level.choices, default=Level.LOW
    )
    owner = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        related_name="owned_project_risks",
    )
    treatment = models.TextField(blank=True, max_length=8000)
    review_date = models.DateField(null=True, blank=True)
    state = models.CharField(
        max_length=16, choices=State.choices, default=State.RAISED
    )
    closure_rationale = models.TextField(blank=True, max_length=8000)
    closed_at = models.DateTimeField(null=True, blank=True)
    version = models.PositiveIntegerField(default=1)
    raised_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name="raised_project_risks",
    )
    idempotency_key = models.CharField(max_length=100, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["state", "-severity", "review_date", "-id"]
        constraints = [
            models.UniqueConstraint(
                fields=["project", "source_type", "source_key"],
                condition=~Q(source_key=""),
                name="unique_project_risk_source",
            ),
            models.UniqueConstraint(
                fields=["project", "idempotency_key"],
                condition=~Q(idempotency_key=""),
                name="unique_project_risk_retry",
            ),
        ]
        indexes = [
            models.Index(
                fields=["project", "state", "severity", "review_date"],
                name="project_risk_state_idx",
            ),
            models.Index(
                fields=["owner", "state", "review_date"],
                name="project_risk_owner_idx",
            ),
            models.Index(
                fields=["project", "source_type", "source_key"],
                name="project_risk_source_idx",
            ),
        ]


class RiskRevision(models.Model):
    project = models.ForeignKey(
        ResearchProject, on_delete=models.CASCADE, related_name="risk_revisions"
    )
    risk = models.ForeignKey(
        RiskRecord, on_delete=models.CASCADE, related_name="revisions"
    )
    revision_number = models.PositiveIntegerField()
    previous_state = models.CharField(max_length=16, choices=RiskRecord.State.choices)
    new_state = models.CharField(max_length=16, choices=RiskRecord.State.choices)
    likelihood = models.CharField(max_length=10, choices=RiskRecord.Level.choices)
    impact = models.CharField(max_length=10, choices=RiskRecord.Level.choices)
    severity = models.CharField(max_length=10, choices=RiskRecord.Level.choices)
    owner_id_snapshot = models.PositiveBigIntegerField(null=True, blank=True)
    treatment = models.TextField(blank=True, max_length=8000)
    review_date = models.DateField(null=True, blank=True)
    closure_rationale = models.TextField(blank=True, max_length=8000)
    actor = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name="project_risk_revisions",
    )
    reason = models.TextField(max_length=8000)
    idempotency_key = models.CharField(max_length=100, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-revision_number"]
        constraints = [
            models.UniqueConstraint(
                fields=["risk", "revision_number"],
                name="unique_project_risk_revision",
            ),
            models.UniqueConstraint(
                fields=["risk", "idempotency_key"],
                condition=~Q(idempotency_key=""),
                name="unique_project_risk_transition_retry",
            ),
        ]
        indexes = [
            models.Index(
                fields=["risk", "-revision_number"], name="project_risk_revision_idx"
            )
        ]


class ProjectRecordLink(models.Model):
    project = models.ForeignKey(
        ResearchProject, on_delete=models.CASCADE, related_name="record_links"
    )
    decision = models.ForeignKey(
        DecisionRecord,
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name="links",
    )
    risk = models.ForeignKey(
        RiskRecord,
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name="links",
    )
    target_type_snapshot = models.CharField(max_length=40)
    target_id_snapshot = models.CharField(max_length=80)
    label_snapshot = models.CharField(max_length=255)
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name="created_project_record_links",
    )
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        constraints = [
            models.CheckConstraint(
                condition=(
                    (Q(decision__isnull=False) & Q(risk__isnull=True))
                    | (Q(decision__isnull=True) & Q(risk__isnull=False))
                ),
                name="project_record_link_one_source",
            ),
            models.UniqueConstraint(
                fields=[
                    "decision", "target_type_snapshot", "target_id_snapshot"
                ],
                name="unique_decision_record_link",
            ),
            models.UniqueConstraint(
                fields=["risk", "target_type_snapshot", "target_id_snapshot"],
                name="unique_risk_record_link",
            ),
        ]
        indexes = [
            models.Index(fields=["decision", "id"], name="decision_record_link_idx"),
            models.Index(fields=["risk", "id"], name="risk_record_link_idx"),
        ]
