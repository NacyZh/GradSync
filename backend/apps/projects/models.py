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
