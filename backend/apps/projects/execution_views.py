from collections import Counter

from django.core.exceptions import PermissionDenied
from django.db.models import Q
from django.shortcuts import get_object_or_404
from drf_spectacular.utils import (
    OpenApiParameter,
    OpenApiResponse,
    extend_schema,
    extend_schema_view,
)
from rest_framework import status, views
from rest_framework.exceptions import ValidationError
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from apps.notifications.models import Notification

from .access_services import project_capabilities
from .decision_risk_services import (
    publish_decision,
    raise_risk,
    supersede_decision,
    transition_risk,
    triage_risk,
)
from .execution_serializers import (
    DecisionWriteSerializer,
    DeliverableSerializer,
    DeliverableSubmissionSerializer,
    DeliverableUpdateSerializer,
    DeliverableWriteSerializer,
    FinalDecisionSerializer,
    GovernanceDecisionSerializer,
    GovernanceDecisionWriteSerializer,
    MilestoneSerializer,
    MilestoneUpdateSerializer,
    MilestoneWriteSerializer,
    RecommendationSerializer,
    RecommendationWriteSerializer,
    RiskRaiseSerializer,
    RiskSerializer,
    RiskTransitionSerializer,
    RiskTriageSerializer,
)
from .execution_services import (
    archive_deliverable,
    archive_milestone,
    create_deliverable,
    create_milestone,
    decide_deliverable,
    recommend_deliverable,
    submit_deliverable,
    update_deliverable,
    update_milestone,
)
from .models import (
    DecisionRecord,
    Deliverable,
    DeliverableRevision,
    ResearchProject,
    RiskRecord,
)

_ERRORS = {
    400: OpenApiResponse(description="Validation error"),
    401: OpenApiResponse(description="Authentication required"),
    403: OpenApiResponse(description="Forbidden"),
    404: OpenApiResponse(description="Not found"),
    409: OpenApiResponse(description="Version conflict"),
}
_READ_ERRORS = {key: value for key, value in _ERRORS.items() if key in {401, 403, 404}}
_PAGE_PARAMETERS = [
    OpenApiParameter("cursor", str, OpenApiParameter.QUERY, required=False),
    OpenApiParameter("pageSize", int, OpenApiParameter.QUERY, required=False),
]


def _project_for(user, project_id):
    project = get_object_or_404(ResearchProject, pk=project_id)
    if not project_capabilities(user, project)["canViewExecutionSummary"]:
        raise PermissionDenied("Project execution access is forbidden.")
    return project


def _page(queryset, request, *, maximum=100):
    try:
        page_size = min(max(int(request.query_params.get("pageSize", 50)), 1), maximum)
        cursor = int(request.query_params.get("cursor", 0) or 0)
    except ValueError as exc:
        raise ValidationError({"cursor": "Enter a valid cursor."}) from exc
    if cursor:
        queryset = queryset.filter(id__gt=cursor)
    rows = list(queryset[: page_size + 1])
    has_more = len(rows) > page_size
    rows = rows[:page_size]
    return rows, {"nextCursor": str(rows[-1].id) if has_more and rows else None}


def _domain_error(exc):
    message = str(exc)
    code = (
        status.HTTP_409_CONFLICT
        if "changed; refresh" in message or "already" in message
        else status.HTTP_400_BAD_REQUEST
    )
    return Response({"message": message}, status=code)


@extend_schema_view(
    get=extend_schema(
        responses={200: OpenApiResponse(description="Execution summary"), **_READ_ERRORS}
    )
)
class ExecutionSummaryView(views.APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request, project_id):
        project = _project_for(request.user, project_id)
        milestones = Counter(project.milestones.values_list("current_status", flat=True))
        deliverables = Counter(project.deliverables.values_list("current_status", flat=True))
        upcoming = [
            {
                "type": "milestone",
                "id": row.id,
                "title": row.title,
                "dueDate": row.target_date,
            }
            for row in project.milestones.filter(archived_at__isnull=True).order_by(
                "target_date", "order"
            )[:5]
        ]
        upcoming.extend(
            {
                "type": "deliverable",
                "id": row.id,
                "title": row.title,
                "dueDate": row.due_date,
            }
            for row in project.deliverables.filter(archived_at__isnull=True).order_by(
                "due_date", "order"
            )[: 10 - len(upcoming)]
        )
        return Response(
            {
                "projectId": project.id,
                "milestoneCounts": dict(milestones),
                "deliverableCounts": dict(deliverables),
                "riskCounts": {},
                "pendingReviews": project.deliverables.filter(
                    current_status=Deliverable.Status.UNDER_REVIEW
                ).count(),
                "missingReports": 0,
                "unresolvedActions": Notification.objects.filter(
                    project=project,
                    recipient=request.user,
                    active_follow_up=True,
                ).count(),
                "upcoming": upcoming[:10],
                "capabilities": project_capabilities(request.user, project),
            }
        )


@extend_schema_view(
    get=extend_schema(
        parameters=_PAGE_PARAMETERS
        + [
            OpenApiParameter("status", str, OpenApiParameter.QUERY),
            OpenApiParameter("q", str, OpenApiParameter.QUERY),
            OpenApiParameter("includeArchived", bool, OpenApiParameter.QUERY),
        ],
        responses={200: MilestoneSerializer(many=True), **_READ_ERRORS},
    ),
    post=extend_schema(
        request=MilestoneWriteSerializer,
        responses={201: MilestoneSerializer, **_ERRORS},
    ),
)
class MilestoneListView(views.APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request, project_id):
        project = _project_for(request.user, project_id)
        queryset = project.milestones.prefetch_related("owners", "deliverables").order_by("id")
        if request.query_params.get("includeArchived", "false").lower() != "true":
            queryset = queryset.filter(archived_at__isnull=True)
        if value := request.query_params.get("status"):
            queryset = queryset.filter(current_status=value)
        if value := request.query_params.get("q", "").strip()[:100]:
            queryset = queryset.filter(Q(title__icontains=value) | Q(description__icontains=value))
        rows, page = _page(queryset, request)
        return Response(
            {
                "results": MilestoneSerializer(rows, many=True).data,
                "page": page,
                "capabilities": project_capabilities(request.user, project),
            }
        )

    def post(self, request, project_id):
        project = _project_for(request.user, project_id)
        serializer = MilestoneWriteSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data
        try:
            milestone = create_milestone(
                actor=request.user,
                project=project,
                title=data["title"],
                description=data.get("description", ""),
                target_date=data["targetDate"],
                owner_ids=data["ownerIds"],
            )
        except ValueError as exc:
            return _domain_error(exc)
        return Response(MilestoneSerializer(milestone).data, status=status.HTTP_201_CREATED)


@extend_schema_view(
    get=extend_schema(responses={200: MilestoneSerializer, **_READ_ERRORS}),
    patch=extend_schema(
        request=MilestoneUpdateSerializer,
        responses={200: MilestoneSerializer, **_ERRORS},
    ),
)
class MilestoneDetailView(views.APIView):
    permission_classes = [IsAuthenticated]

    def _get(self, request, project_id, milestone_id):
        project = _project_for(request.user, project_id)
        return get_object_or_404(
            project.milestones.prefetch_related("owners", "deliverables"),
            pk=milestone_id,
        )

    def get(self, request, project_id, milestone_id):
        return Response(MilestoneSerializer(self._get(request, project_id, milestone_id)).data)

    def patch(self, request, project_id, milestone_id):
        milestone = self._get(request, project_id, milestone_id)
        serializer = MilestoneUpdateSerializer(data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data
        if "expectedVersion" not in data:
            raise ValidationError({"expectedVersion": "This field is required."})
        try:
            result = update_milestone(
                actor=request.user,
                milestone=milestone,
                expected_version=data["expectedVersion"],
                title=data.get("title"),
                description=data.get("description"),
                target_date=data.get("targetDate"),
                owner_ids=data.get("ownerIds"),
            )
        except ValueError as exc:
            return _domain_error(exc)
        return Response(MilestoneSerializer(result).data)


@extend_schema_view(
    post=extend_schema(
        request=MilestoneUpdateSerializer,
        responses={200: MilestoneSerializer, **_ERRORS},
    )
)
class MilestoneArchiveView(views.APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request, project_id, milestone_id):
        project = _project_for(request.user, project_id)
        milestone = get_object_or_404(project.milestones, pk=milestone_id)
        try:
            result = archive_milestone(
                actor=request.user,
                milestone=milestone,
                expected_version=int(request.data.get("expectedVersion", 0)),
            )
        except (TypeError, ValueError) as exc:
            return _domain_error(exc)
        return Response(MilestoneSerializer(result).data)


@extend_schema_view(
    get=extend_schema(
        parameters=_PAGE_PARAMETERS
        + [
            OpenApiParameter("milestoneId", int, OpenApiParameter.QUERY),
            OpenApiParameter("status", str, OpenApiParameter.QUERY),
            OpenApiParameter("assigneeId", int, OpenApiParameter.QUERY),
            OpenApiParameter("q", str, OpenApiParameter.QUERY),
            OpenApiParameter("includeArchived", bool, OpenApiParameter.QUERY),
        ],
        responses={200: DeliverableSerializer(many=True), **_READ_ERRORS},
    ),
    post=extend_schema(
        request=DeliverableWriteSerializer,
        responses={201: DeliverableSerializer, **_ERRORS},
    ),
)
class DeliverableListView(views.APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request, project_id):
        project = _project_for(request.user, project_id)
        queryset = (
            project.deliverables.select_related("milestone", "project")
            .prefetch_related(
                "assignees__user",
                "task_links",
                "revisions__evidence",
                "revisions__recommendations__reviewer",
            )
            .order_by("id")
        )
        if request.query_params.get("includeArchived", "false").lower() != "true":
            queryset = queryset.filter(archived_at__isnull=True)
        if value := request.query_params.get("milestoneId"):
            queryset = queryset.filter(milestone_id=value)
        if value := request.query_params.get("status"):
            queryset = queryset.filter(current_status=value)
        if value := request.query_params.get("assigneeId"):
            queryset = queryset.filter(assignees__user_id=value, assignees__removed_at__isnull=True)
        if value := request.query_params.get("q", "").strip()[:100]:
            queryset = queryset.filter(Q(title__icontains=value) | Q(description__icontains=value))
        rows, page = _page(queryset.distinct(), request)
        capabilities = project_capabilities(request.user, project)
        return Response(
            {
                "results": DeliverableSerializer(
                    rows,
                    many=True,
                    context={"request": request, "capabilities": capabilities},
                ).data,
                "page": page,
                "capabilities": capabilities,
            }
        )

    def post(self, request, project_id):
        project = _project_for(request.user, project_id)
        serializer = DeliverableWriteSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data
        milestone = get_object_or_404(project.milestones, pk=data["milestoneId"])
        try:
            result = create_deliverable(
                actor=request.user,
                milestone=milestone,
                title=data["title"],
                description=data.get("description", ""),
                acceptance_criteria=data["acceptanceCriteria"],
                due_date=data["dueDate"],
                required=data["required"],
                assignee_ids=data["assigneeIds"],
                task_ids=data.get("taskIds", []),
                reviewer_required=data.get("reviewerRequired", False),
                reviewer_ids=data.get("reviewerIds", []),
            )
        except ValueError as exc:
            return _domain_error(exc)
        return Response(
            DeliverableSerializer(result, context={"request": request}).data,
            status=status.HTTP_201_CREATED,
        )


@extend_schema_view(
    get=extend_schema(responses={200: DeliverableSerializer, **_READ_ERRORS}),
    patch=extend_schema(
        request=DeliverableUpdateSerializer,
        responses={200: DeliverableSerializer, **_ERRORS},
    ),
)
class DeliverableDetailView(views.APIView):
    permission_classes = [IsAuthenticated]

    def _get(self, request, project_id, deliverable_id):
        project = _project_for(request.user, project_id)
        return get_object_or_404(
            project.deliverables.select_related("project", "milestone").prefetch_related(
                "assignees__user", "task_links", "revisions__evidence"
            ),
            pk=deliverable_id,
        )

    def get(self, request, project_id, deliverable_id):
        result = self._get(request, project_id, deliverable_id)
        return Response(DeliverableSerializer(result, context={"request": request}).data)

    def patch(self, request, project_id, deliverable_id):
        deliverable = self._get(request, project_id, deliverable_id)
        serializer = DeliverableUpdateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data
        planning_map = {
            "title": "title",
            "description": "description",
            "acceptanceCriteria": "acceptance_criteria",
            "dueDate": "due_date",
            "required": "required",
            "assigneeIds": "assignee_ids",
        }
        planning = {
            target: data[source] for source, target in planning_map.items() if source in data
        }
        try:
            result = update_deliverable(
                actor=request.user,
                deliverable=deliverable,
                expected_version=data["expectedVersion"],
                planning=planning or None,
                progress_percent=data.get("progressPercent"),
                work_status=data.get("workStatus"),
                blocker_summary=data.get("blockerSummary"),
            )
        except ValueError as exc:
            return _domain_error(exc)
        return Response(DeliverableSerializer(result, context={"request": request}).data)


@extend_schema_view(
    post=extend_schema(
        request=DeliverableSubmissionSerializer,
        responses={201: OpenApiResponse(description="Submitted revision"), **_ERRORS},
    )
)
class DeliverableSubmitView(views.APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request, project_id, deliverable_id):
        project = _project_for(request.user, project_id)
        deliverable = get_object_or_404(project.deliverables, pk=deliverable_id)
        serializer = DeliverableSubmissionSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data
        if deliverable.version != data["expectedVersion"]:
            return _domain_error(ValueError("The deliverable changed; refresh and try again."))
        evidence = []
        for item in data["evidence"]:
            source_type = item["type"]
            mapped = {"label": item["label"]}
            if source_type == "external_url":
                mapped["external_url"] = item["url"]
            else:
                mapped[
                    {
                        "project_material": "project_material_id",
                        "task": "task_id",
                        "report": "weekly_progress_report_id",
                    }[source_type]
                ] = item["sourceId"]
            evidence.append(mapped)
        try:
            revision = submit_deliverable(
                actor=request.user,
                deliverable=deliverable,
                description=data["description"],
                evidence=evidence,
                idempotency_key=data["idempotencyKey"],
            )
        except ValueError as exc:
            return _domain_error(exc)
        from .execution_serializers import DeliverableRevisionSerializer

        return Response(
            DeliverableRevisionSerializer(revision, context={"request": request}).data,
            status=status.HTTP_201_CREATED,
        )


@extend_schema_view(
    post=extend_schema(
        request=RecommendationWriteSerializer,
        responses={201: RecommendationSerializer, **_ERRORS},
    )
)
class DeliverableRecommendationView(views.APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request, project_id, deliverable_id):
        project = _project_for(request.user, project_id)
        deliverable = get_object_or_404(project.deliverables, pk=deliverable_id)
        serializer = RecommendationWriteSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        revision = get_object_or_404(
            DeliverableRevision,
            pk=serializer.validated_data["revisionId"],
            deliverable=deliverable,
        )
        try:
            result = recommend_deliverable(
                actor=request.user,
                revision=revision,
                recommendation=serializer.validated_data["recommendation"],
                rationale=serializer.validated_data["rationale"],
            )
        except ValueError as exc:
            return _domain_error(exc)
        return Response(RecommendationSerializer(result).data, status=status.HTTP_201_CREATED)


@extend_schema_view(
    post=extend_schema(
        request=DecisionWriteSerializer,
        responses={201: FinalDecisionSerializer, **_ERRORS},
    )
)
class DeliverableDecisionView(views.APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request, project_id, deliverable_id):
        project = _project_for(request.user, project_id)
        deliverable = get_object_or_404(project.deliverables, pk=deliverable_id)
        serializer = DecisionWriteSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data
        if deliverable.version != data["expectedVersion"]:
            return _domain_error(ValueError("The deliverable changed; refresh and try again."))
        revision = get_object_or_404(
            DeliverableRevision, pk=data["revisionId"], deliverable=deliverable
        )
        try:
            result = decide_deliverable(
                actor=request.user,
                revision=revision,
                decision=data["decision"],
                rationale=data.get("rationale", ""),
                idempotency_key=data["idempotencyKey"],
            )
        except ValueError as exc:
            return _domain_error(exc)
        return Response(FinalDecisionSerializer(result).data, status=status.HTTP_201_CREATED)


@extend_schema_view(
    post=extend_schema(
        request=DeliverableUpdateSerializer,
        responses={200: DeliverableSerializer, **_ERRORS},
    )
)
class DeliverableArchiveView(views.APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request, project_id, deliverable_id):
        project = _project_for(request.user, project_id)
        deliverable = get_object_or_404(project.deliverables, pk=deliverable_id)
        try:
            result = archive_deliverable(
                actor=request.user,
                deliverable=deliverable,
                expected_version=int(request.data.get("expectedVersion", 0)),
            )
        except (TypeError, ValueError) as exc:
            return _domain_error(exc)
        return Response(DeliverableSerializer(result, context={"request": request}).data)


@extend_schema_view(
    get=extend_schema(
        parameters=_PAGE_PARAMETERS
        + [
            OpenApiParameter("status", str, OpenApiParameter.QUERY),
            OpenApiParameter("q", str, OpenApiParameter.QUERY),
        ],
        responses={200: GovernanceDecisionSerializer(many=True), **_READ_ERRORS},
    ),
    post=extend_schema(
        request=GovernanceDecisionWriteSerializer,
        responses={201: GovernanceDecisionSerializer, **_ERRORS},
    ),
)
class DecisionListView(views.APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request, project_id):
        project = _project_for(request.user, project_id)
        rows = (
            DecisionRecord.objects.filter(project=project)
            .select_related("owner", "published_by", "supersedes")
            .prefetch_related("links")
        )
        if request.query_params.get("status"):
            rows = rows.filter(status=request.query_params["status"])
        query = request.query_params.get("q", "").strip()
        if query:
            rows = rows.filter(Q(title__icontains=query) | Q(outcome__icontains=query))
        page, metadata = _page(rows, request)
        return Response(
            {
                "results": GovernanceDecisionSerializer(page, many=True).data,
                "page": metadata,
                "canPublish": project_capabilities(request.user, project)["canPublishDecisions"],
            }
        )

    def post(self, request, project_id):
        project = _project_for(request.user, project_id)
        serializer = GovernanceDecisionWriteSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data
        try:
            decision = publish_decision(
                actor=request.user,
                project=project,
                title=data["title"],
                context=data["context"],
                options_considered=data["optionsConsidered"],
                outcome=data["outcome"],
                rationale=data["rationale"],
                owner_id=data["ownerId"],
                effective_date=data["effectiveDate"],
                links=data.get("links", []),
                idempotency_key=data.get("idempotencyKey", ""),
            )
        except (PermissionDenied, ValueError) as exc:
            return _domain_error(exc)
        return Response(
            GovernanceDecisionSerializer(decision).data,
            status=status.HTTP_201_CREATED,
        )


@extend_schema_view(
    get=extend_schema(responses={200: GovernanceDecisionSerializer, **_READ_ERRORS})
)
class DecisionDetailView(views.APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request, project_id, decision_id):
        project = _project_for(request.user, project_id)
        decision = get_object_or_404(
            DecisionRecord.objects.select_related(
                "owner", "published_by", "supersedes"
            ).prefetch_related("links"),
            project=project,
            pk=decision_id,
        )
        return Response(GovernanceDecisionSerializer(decision).data)


@extend_schema_view(
    post=extend_schema(
        request=GovernanceDecisionWriteSerializer,
        responses={201: GovernanceDecisionSerializer, **_ERRORS},
    )
)
class DecisionSupersedeView(views.APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request, project_id, decision_id):
        project = _project_for(request.user, project_id)
        predecessor = get_object_or_404(DecisionRecord, project=project, pk=decision_id)
        serializer = GovernanceDecisionWriteSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data
        try:
            decision = supersede_decision(
                actor=request.user,
                predecessor=predecessor,
                title=data["title"],
                context=data["context"],
                options_considered=data["optionsConsidered"],
                outcome=data["outcome"],
                rationale=data["rationale"],
                owner_id=data["ownerId"],
                effective_date=data["effectiveDate"],
                links=data.get("links", []),
                idempotency_key=data.get("idempotencyKey", ""),
            )
        except (PermissionDenied, ValueError) as exc:
            return _domain_error(exc)
        return Response(
            GovernanceDecisionSerializer(decision).data,
            status=status.HTTP_201_CREATED,
        )


@extend_schema_view(
    get=extend_schema(
        parameters=_PAGE_PARAMETERS
        + [
            OpenApiParameter("state", str, OpenApiParameter.QUERY),
            OpenApiParameter("severity", str, OpenApiParameter.QUERY),
            OpenApiParameter("ownerId", int, OpenApiParameter.QUERY),
            OpenApiParameter("q", str, OpenApiParameter.QUERY),
        ],
        responses={200: RiskSerializer(many=True), **_READ_ERRORS},
    ),
    post=extend_schema(request=RiskRaiseSerializer, responses={201: RiskSerializer, **_ERRORS}),
)
class RiskListView(views.APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request, project_id):
        project = _project_for(request.user, project_id)
        rows = (
            RiskRecord.objects.filter(project=project)
            .select_related("owner", "raised_by")
            .prefetch_related("links", "revisions__actor")
        )
        for parameter, field in [
            ("state", "state"),
            ("severity", "severity"),
            ("ownerId", "owner_id"),
        ]:
            if request.query_params.get(parameter):
                rows = rows.filter(**{field: request.query_params[parameter]})
        query = request.query_params.get("q", "").strip()
        if query:
            rows = rows.filter(Q(title__icontains=query) | Q(description__icontains=query))
        page, metadata = _page(rows, request)
        capabilities = project_capabilities(request.user, project)
        return Response(
            {
                "results": RiskSerializer(page, many=True).data,
                "page": metadata,
                "canRaise": capabilities["canRaiseRisks"],
                "canTriage": capabilities["canTriageRisks"],
            }
        )

    def post(self, request, project_id):
        project = _project_for(request.user, project_id)
        serializer = RiskRaiseSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data
        source_id = data.get("sourceId")
        try:
            risk = raise_risk(
                actor=request.user,
                project=project,
                title=data["title"],
                description=data["description"],
                source_type=data["sourceType"],
                source_key=(f"{data['sourceType']}:{source_id}" if source_id else ""),
                links=data.get("links", []),
                idempotency_key=data.get("idempotencyKey", ""),
            )
        except (PermissionDenied, ValueError) as exc:
            return _domain_error(exc)
        return Response(RiskSerializer(risk).data, status=status.HTTP_201_CREATED)


@extend_schema_view(
    get=extend_schema(responses={200: RiskSerializer, **_READ_ERRORS}),
    patch=extend_schema(request=RiskTriageSerializer, responses={200: RiskSerializer, **_ERRORS}),
)
class RiskDetailView(views.APIView):
    permission_classes = [IsAuthenticated]

    def get_risk(self, request, project_id, risk_id):
        project = _project_for(request.user, project_id)
        return get_object_or_404(
            RiskRecord.objects.select_related("owner", "raised_by").prefetch_related(
                "links", "revisions__actor"
            ),
            project=project,
            pk=risk_id,
        )

    def get(self, request, project_id, risk_id):
        return Response(RiskSerializer(self.get_risk(request, project_id, risk_id)).data)

    def patch(self, request, project_id, risk_id):
        risk = self.get_risk(request, project_id, risk_id)
        serializer = RiskTriageSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data
        try:
            risk = triage_risk(
                actor=request.user,
                risk=risk,
                expected_version=data["expectedVersion"],
                likelihood=data["likelihood"],
                impact=data["impact"],
                owner_id=data["ownerId"],
                treatment=data["treatment"],
                review_date=data["reviewDate"],
                reason=data.get("reason", "Risk triaged"),
            )
        except (PermissionDenied, ValueError) as exc:
            return _domain_error(exc)
        return Response(RiskSerializer(risk).data)


@extend_schema_view(
    post=extend_schema(request=RiskTransitionSerializer, responses={200: RiskSerializer, **_ERRORS})
)
class RiskTransitionView(RiskDetailView):
    def post(self, request, project_id, risk_id):
        risk = self.get_risk(request, project_id, risk_id)
        serializer = RiskTransitionSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data
        try:
            risk = transition_risk(
                actor=request.user,
                risk=risk,
                expected_version=data["expectedVersion"],
                action=data["action"],
                reason=data["reason"],
                idempotency_key=data["idempotencyKey"],
                owner_id=data.get("ownerId"),
                review_date=data.get("reviewDate"),
                evidence_links=data.get("evidenceLinks", []),
            )
        except (PermissionDenied, ValueError) as exc:
            return _domain_error(exc)
        return Response(RiskSerializer(risk).data)
