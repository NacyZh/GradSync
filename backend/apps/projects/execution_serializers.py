from rest_framework import serializers

from .access_services import project_capabilities
from .models import (
    DecisionRecord,
    Deliverable,
    DeliverableEvidence,
    DeliverableFinalDecision,
    DeliverableReviewRecommendation,
    DeliverableRevision,
    Milestone,
    RiskRecord,
    RiskRevision,
)


class MemberSummarySerializer(serializers.Serializer):
    id = serializers.IntegerField(source="user.id")
    name = serializers.CharField(source="user.name")
    role = serializers.SerializerMethodField()

    def get_role(self, obj):
        project_id = (
            obj.deliverable.project_id if hasattr(obj, "deliverable") else obj.milestone.project_id
        )
        membership = obj.user.project_memberships.filter(
            project_id=project_id, status="active"
        ).first()
        return membership.role if membership else ""


class ExecutionCapabilitiesSerializer(serializers.Serializer):
    canManageMilestones = serializers.BooleanField()
    canManageDeliverables = serializers.BooleanField()
    canSubmitAssignedDeliverables = serializers.BooleanField()
    canRecommendDeliverables = serializers.BooleanField()
    canDecideDeliverables = serializers.BooleanField()
    canPublishDecisions = serializers.BooleanField()
    canRaiseRisks = serializers.BooleanField()
    canTriageRisks = serializers.BooleanField()


class MilestoneWriteSerializer(serializers.Serializer):
    title = serializers.CharField(max_length=255)
    description = serializers.CharField(
        max_length=8000, required=False, allow_blank=True, default=""
    )
    targetDate = serializers.DateField()
    ownerIds = serializers.ListField(
        child=serializers.IntegerField(min_value=1),
        min_length=1,
        max_length=50,
        allow_empty=False,
    )
    order = serializers.IntegerField(min_value=0, required=False)

    def validate_ownerIds(self, value):
        if len(value) != len(set(value)):
            raise serializers.ValidationError("Select each owner once.")
        return value


class MilestoneUpdateSerializer(MilestoneWriteSerializer):
    expectedVersion = serializers.IntegerField(min_value=1)
    title = serializers.CharField(max_length=255, required=False)
    targetDate = serializers.DateField(required=False)
    ownerIds = serializers.ListField(
        child=serializers.IntegerField(min_value=1),
        min_length=1,
        max_length=50,
        required=False,
    )


class MilestoneSerializer(serializers.ModelSerializer):
    projectId = serializers.IntegerField(source="project_id")
    targetDate = serializers.DateField(source="target_date")
    ownerIds = serializers.SerializerMethodField()
    status = serializers.CharField(source="current_status")
    requiredDeliverables = serializers.SerializerMethodField()
    acceptedDeliverables = serializers.SerializerMethodField()
    completedAt = serializers.DateTimeField(source="completed_at")
    archivedAt = serializers.DateTimeField(source="archived_at")
    createdAt = serializers.DateTimeField(source="created_at")
    updatedAt = serializers.DateTimeField(source="updated_at")

    class Meta:
        model = Milestone
        fields = [
            "id",
            "projectId",
            "title",
            "description",
            "targetDate",
            "ownerIds",
            "order",
            "status",
            "version",
            "requiredDeliverables",
            "acceptedDeliverables",
            "completedAt",
            "archivedAt",
            "createdAt",
            "updatedAt",
        ]

    def get_ownerIds(self, obj):
        return list(obj.owners.values_list("user_id", flat=True))

    def get_requiredDeliverables(self, obj):
        return obj.deliverables.filter(required=True, archived_at__isnull=True).count()

    def get_acceptedDeliverables(self, obj):
        return obj.deliverables.filter(
            required=True, current_status=Deliverable.Status.ACCEPTED
        ).count()


class EvidenceWriteSerializer(serializers.Serializer):
    type = serializers.ChoiceField(choices=["project_material", "task", "report", "external_url"])
    sourceId = serializers.IntegerField(min_value=1, required=False)
    url = serializers.URLField(max_length=2048, required=False)
    label = serializers.CharField(max_length=255)

    def validate(self, attrs):
        if attrs["type"] == "external_url":
            if not attrs.get("url"):
                raise serializers.ValidationError({"url": "Enter an HTTPS URL."})
        elif not attrs.get("sourceId"):
            raise serializers.ValidationError({"sourceId": "Select an evidence source."})
        return attrs

    def to_service_value(self):
        source_type = self.validated_data["type"]
        result = {"label": self.validated_data["label"]}
        if source_type == "external_url":
            result["external_url"] = self.validated_data["url"]
        else:
            result[
                {
                    "project_material": "project_material_id",
                    "task": "task_id",
                    "report": "weekly_progress_report_id",
                }[source_type]
            ] = self.validated_data["sourceId"]
        return result


class EvidenceSerializer(serializers.ModelSerializer):
    type = serializers.CharField(source="source_type_snapshot")
    sourceId = serializers.SerializerMethodField()
    url = serializers.CharField(source="external_url")
    label = serializers.CharField(source="label_snapshot")
    available = serializers.SerializerMethodField()
    sourceTypeSnapshot = serializers.CharField(source="source_type_snapshot")
    sourceIdSnapshot = serializers.CharField(source="source_id_snapshot")

    class Meta:
        model = DeliverableEvidence
        fields = [
            "id",
            "type",
            "sourceId",
            "url",
            "label",
            "available",
            "sourceTypeSnapshot",
            "sourceIdSnapshot",
        ]

    def get_sourceId(self, obj):
        return obj.project_material_id or obj.task_id or obj.weekly_progress_report_id

    def get_available(self, obj):
        if obj.source_type_snapshot == DeliverableEvidence.SourceType.URL:
            return bool(obj.external_url)
        return self.get_sourceId(obj) is not None


class RecommendationSerializer(serializers.ModelSerializer):
    revisionId = serializers.IntegerField(source="revision_id")
    reviewer = serializers.SerializerMethodField()
    createdAt = serializers.DateTimeField(source="created_at")

    class Meta:
        model = DeliverableReviewRecommendation
        fields = [
            "id",
            "revisionId",
            "recommendation",
            "rationale",
            "reviewer",
            "createdAt",
        ]

    def get_reviewer(self, obj):
        return {"id": obj.reviewer_id, "name": obj.reviewer.name}


class FinalDecisionSerializer(serializers.ModelSerializer):
    revisionId = serializers.IntegerField(source="revision_id")
    decidedBy = serializers.SerializerMethodField()
    decidedAt = serializers.DateTimeField(source="decided_at")

    class Meta:
        model = DeliverableFinalDecision
        fields = [
            "id",
            "revisionId",
            "decision",
            "rationale",
            "decidedBy",
            "decidedAt",
        ]

    def get_decidedBy(self, obj):
        return {"id": obj.decided_by_id, "name": obj.decided_by.name}


class DeliverableRevisionSerializer(serializers.ModelSerializer):
    revisionNumber = serializers.IntegerField(source="revision_number")
    criteriaSnapshot = serializers.CharField(source="criteria_snapshot")
    descriptionSnapshot = serializers.CharField(source="description_snapshot")
    submittedBy = serializers.SerializerMethodField()
    submittedAt = serializers.DateTimeField(source="submitted_at")
    evidence = EvidenceSerializer(many=True)
    recommendations = serializers.SerializerMethodField()
    finalDecision = serializers.SerializerMethodField()

    class Meta:
        model = DeliverableRevision
        fields = [
            "id",
            "revisionNumber",
            "state",
            "criteriaSnapshot",
            "descriptionSnapshot",
            "submittedBy",
            "submittedAt",
            "evidence",
            "recommendations",
            "finalDecision",
        ]

    def get_submittedBy(self, obj):
        return {"id": obj.submitted_by_id, "name": obj.submitted_by.name}

    def get_recommendations(self, obj):
        request = self.context.get("request")
        capabilities = project_capabilities(request.user, obj.project) if request else {}
        if not (
            capabilities.get("canRecommendDeliverables")
            or capabilities.get("canDecideDeliverables")
            or capabilities.get("canViewExecutionOperations")
        ):
            return []
        rows = obj.recommendations.filter(superseded_at__isnull=True).select_related("reviewer")
        return RecommendationSerializer(rows, many=True).data

    def get_finalDecision(self, obj):
        try:
            decision = obj.final_decision
        except DeliverableFinalDecision.DoesNotExist:
            return None
        return FinalDecisionSerializer(decision).data


class DeliverableWriteSerializer(serializers.Serializer):
    milestoneId = serializers.IntegerField(min_value=1)
    title = serializers.CharField(max_length=255)
    description = serializers.CharField(
        max_length=8000, required=False, allow_blank=True, default=""
    )
    acceptanceCriteria = serializers.CharField(max_length=8000)
    dueDate = serializers.DateField()
    required = serializers.BooleanField(default=True)
    assigneeIds = serializers.ListField(
        child=serializers.IntegerField(min_value=1), min_length=1, max_length=50
    )
    taskIds = serializers.ListField(
        child=serializers.IntegerField(min_value=1),
        max_length=100,
        required=False,
        default=list,
    )
    reviewerRequired = serializers.BooleanField(required=False, default=False)
    reviewerIds = serializers.ListField(
        child=serializers.IntegerField(min_value=1),
        max_length=20,
        required=False,
        default=list,
    )


class DeliverableUpdateSerializer(serializers.Serializer):
    expectedVersion = serializers.IntegerField(min_value=1)
    title = serializers.CharField(max_length=255, required=False)
    description = serializers.CharField(max_length=8000, required=False, allow_blank=True)
    acceptanceCriteria = serializers.CharField(max_length=8000, required=False)
    dueDate = serializers.DateField(required=False)
    required = serializers.BooleanField(required=False)
    assigneeIds = serializers.ListField(
        child=serializers.IntegerField(min_value=1),
        min_length=1,
        max_length=50,
        required=False,
    )
    progressPercent = serializers.IntegerField(min_value=0, max_value=100, required=False)
    workStatus = serializers.ChoiceField(
        choices=["planned", "in_progress", "blocked"], required=False
    )
    blockerSummary = serializers.CharField(max_length=2000, required=False, allow_blank=True)


class DeliverableSubmissionSerializer(serializers.Serializer):
    expectedVersion = serializers.IntegerField(min_value=1)
    description = serializers.CharField(max_length=8000)
    evidence = EvidenceWriteSerializer(many=True, min_length=1, max_length=100)
    idempotencyKey = serializers.CharField(min_length=8, max_length=100)


class RecommendationWriteSerializer(serializers.Serializer):
    revisionId = serializers.IntegerField(min_value=1)
    recommendation = serializers.ChoiceField(choices=["accept", "return"])
    rationale = serializers.CharField(max_length=8000)
    idempotencyKey = serializers.CharField(min_length=8, max_length=100, required=False)


class DecisionWriteSerializer(serializers.Serializer):
    revisionId = serializers.IntegerField(min_value=1)
    decision = serializers.ChoiceField(choices=["accepted", "returned"])
    rationale = serializers.CharField(max_length=8000, required=False, allow_blank=True)
    expectedVersion = serializers.IntegerField(min_value=1)
    idempotencyKey = serializers.CharField(min_length=8, max_length=100)


class DeliverableSerializer(serializers.ModelSerializer):
    projectId = serializers.IntegerField(source="project_id")
    milestoneId = serializers.IntegerField(source="milestone_id")
    acceptanceCriteria = serializers.CharField(source="acceptance_criteria")
    dueDate = serializers.DateField(source="due_date")
    reviewerRequired = serializers.BooleanField(source="reviewer_required")
    status = serializers.CharField(source="current_status")
    progressPercent = serializers.IntegerField(source="progress_percent")
    blockerSummary = serializers.CharField(source="blocker_summary")
    assignees = MemberSummarySerializer(many=True)
    taskIds = serializers.SerializerMethodField()
    acceptedRevisionId = serializers.IntegerField(source="accepted_revision_id")
    revisions = serializers.SerializerMethodField()
    capabilities = serializers.SerializerMethodField()

    class Meta:
        model = Deliverable
        fields = [
            "id",
            "projectId",
            "milestoneId",
            "title",
            "description",
            "acceptanceCriteria",
            "dueDate",
            "required",
            "reviewerRequired",
            "status",
            "progressPercent",
            "blockerSummary",
            "assignees",
            "taskIds",
            "version",
            "acceptedRevisionId",
            "revisions",
            "capabilities",
        ]

    def get_taskIds(self, obj):
        return [link.task_id for link in obj.task_links.all()]

    def get_revisions(self, obj):
        rows = list(obj.revisions.all())[:25]
        return DeliverableRevisionSerializer(rows, many=True, context=self.context).data

    def get_capabilities(self, obj):
        if "capabilities" in self.context:
            return self.context["capabilities"]
        request = self.context.get("request")
        return project_capabilities(request.user, obj.project) if request else {}


class GovernanceDecisionWriteSerializer(serializers.Serializer):
    title = serializers.CharField(max_length=255)
    context = serializers.CharField(max_length=8000)
    optionsConsidered = serializers.ListField(
        child=serializers.CharField(max_length=1000), min_length=1, max_length=20
    )
    outcome = serializers.CharField(max_length=8000)
    rationale = serializers.CharField(max_length=8000)
    ownerId = serializers.IntegerField(min_value=1)
    effectiveDate = serializers.DateField()
    links = serializers.ListField(child=serializers.DictField(), required=False, max_length=100)
    idempotencyKey = serializers.CharField(
        min_length=8, max_length=100, required=False, allow_blank=True
    )


class RecordLinkSerializer(serializers.Serializer):
    id = serializers.IntegerField()
    targetType = serializers.CharField(source="target_type_snapshot")
    targetId = serializers.CharField(source="target_id_snapshot")
    label = serializers.CharField(source="label_snapshot")
    available = serializers.SerializerMethodField()

    def get_available(self, obj):
        return True


class GovernanceDecisionSerializer(serializers.ModelSerializer):
    projectId = serializers.IntegerField(source="project_id")
    optionsConsidered = serializers.JSONField(source="options_considered")
    owner = serializers.SerializerMethodField()
    effectiveDate = serializers.DateField(source="effective_date")
    supersedesId = serializers.IntegerField(source="supersedes_id", allow_null=True)
    supersededById = serializers.SerializerMethodField()
    publishedBy = serializers.SerializerMethodField()
    publishedAt = serializers.DateTimeField(source="published_at")
    links = RecordLinkSerializer(many=True)

    class Meta:
        model = DecisionRecord
        fields = [
            "id",
            "projectId",
            "title",
            "context",
            "optionsConsidered",
            "outcome",
            "rationale",
            "owner",
            "effectiveDate",
            "status",
            "supersedesId",
            "supersededById",
            "publishedBy",
            "publishedAt",
            "links",
        ]

    def _user(self, user):
        return {"id": user.id, "displayName": user.name, "role": user.global_role}

    def get_owner(self, obj):
        return self._user(obj.owner)

    def get_publishedBy(self, obj):
        return self._user(obj.published_by)

    def get_supersededById(self, obj):
        try:
            return obj.superseded_by.id
        except DecisionRecord.DoesNotExist:
            return None


class RiskRaiseSerializer(serializers.Serializer):
    title = serializers.CharField(max_length=255)
    description = serializers.CharField(max_length=8000)
    sourceType = serializers.ChoiceField(
        choices=RiskRecord.SourceType.choices,
        required=False,
        default=RiskRecord.SourceType.MANUAL,
    )
    sourceId = serializers.CharField(required=False, allow_null=True, allow_blank=True)
    links = serializers.ListField(child=serializers.DictField(), required=False, max_length=100)
    idempotencyKey = serializers.CharField(
        min_length=8, max_length=100, required=False, allow_blank=True
    )


class RiskTriageSerializer(serializers.Serializer):
    expectedVersion = serializers.IntegerField(min_value=1)
    likelihood = serializers.ChoiceField(choices=RiskRecord.Level.choices)
    impact = serializers.ChoiceField(choices=RiskRecord.Level.choices)
    ownerId = serializers.IntegerField(min_value=1)
    treatment = serializers.CharField(max_length=8000)
    reviewDate = serializers.DateField()
    reason = serializers.CharField(max_length=8000, required=False, allow_blank=True)


class RiskTransitionSerializer(serializers.Serializer):
    expectedVersion = serializers.IntegerField(min_value=1)
    action = serializers.ChoiceField(choices=["start_mitigation", "accept", "resolve", "reopen"])
    reason = serializers.CharField(max_length=8000)
    ownerId = serializers.IntegerField(required=False, allow_null=True)
    reviewDate = serializers.DateField(required=False, allow_null=True)
    evidenceLinks = serializers.ListField(
        child=serializers.DictField(), required=False, max_length=100
    )
    idempotencyKey = serializers.CharField(min_length=8, max_length=100)


class RiskRevisionSerializer(serializers.ModelSerializer):
    revisionNumber = serializers.IntegerField(source="revision_number")
    previousState = serializers.CharField(source="previous_state")
    newState = serializers.CharField(source="new_state")
    reviewDate = serializers.DateField(source="review_date", allow_null=True)
    actor = serializers.SerializerMethodField()
    createdAt = serializers.DateTimeField(source="created_at")

    class Meta:
        model = RiskRevision
        fields = [
            "revisionNumber",
            "previousState",
            "newState",
            "likelihood",
            "impact",
            "severity",
            "reviewDate",
            "actor",
            "reason",
            "createdAt",
        ]

    def get_actor(self, obj):
        return {
            "id": obj.actor_id,
            "displayName": obj.actor.name,
            "role": obj.actor.global_role,
        }


class RiskSerializer(serializers.ModelSerializer):
    projectId = serializers.IntegerField(source="project_id")
    sourceType = serializers.CharField(source="source_type")
    matrixExplanation = serializers.SerializerMethodField()
    owner = serializers.SerializerMethodField()
    reviewDate = serializers.DateField(source="review_date", allow_null=True)
    closureRationale = serializers.CharField(source="closure_rationale")
    raisedBy = serializers.SerializerMethodField()
    createdAt = serializers.DateTimeField(source="created_at")
    updatedAt = serializers.DateTimeField(source="updated_at")
    links = RecordLinkSerializer(many=True)
    revisions = RiskRevisionSerializer(many=True)

    class Meta:
        model = RiskRecord
        fields = [
            "id",
            "projectId",
            "title",
            "description",
            "sourceType",
            "likelihood",
            "impact",
            "severity",
            "matrixExplanation",
            "owner",
            "treatment",
            "reviewDate",
            "state",
            "closureRationale",
            "version",
            "raisedBy",
            "createdAt",
            "updatedAt",
            "links",
            "revisions",
        ]

    def get_matrixExplanation(self, obj):
        return (
            f"{obj.likelihood} likelihood and {obj.impact} impact produce {obj.severity} severity."
        )

    def get_owner(self, obj):
        if not obj.owner_id:
            return None
        return {
            "id": obj.owner_id,
            "displayName": obj.owner.name,
            "role": obj.owner.global_role,
        }

    def get_raisedBy(self, obj):
        return {
            "id": obj.raised_by_id,
            "displayName": obj.raised_by.name,
            "role": obj.raised_by.global_role,
        }
