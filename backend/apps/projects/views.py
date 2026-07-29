import re

from django.contrib.auth import get_user_model
from django.core.exceptions import PermissionDenied as DjangoPermissionDenied
from django.core.exceptions import ValidationError as DjangoValidationError
from django.shortcuts import get_object_or_404
from django.utils import timezone
from drf_spectacular.utils import (
    OpenApiParameter,
    OpenApiResponse,
    extend_schema,
    extend_schema_view,
)
from rest_framework import mixins, status, views, viewsets
from rest_framework.decorators import action
from rest_framework.exceptions import PermissionDenied, ValidationError
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from apps.common.downloads import DownloadUnavailable
from apps.submissions.models import (
    DraftVersion,
    SubmissionReviewAssignment,
    WeeklyProgressReport,
    WritingVersion,
)
from apps.submissions.review_assignment_services import (
    assign_reviewer,
    remove_review_assignment,
)
from apps.submissions.serializers import SubmissionReviewAssignmentSerializer

from .access_services import project_capabilities
from .closeout_serializers import (
    CloseoutDispositionSerializer,
    ProjectCloseoutPreflightSerializer,
    ProjectCloseoutResultSerializer,
)
from .closeout_services import (
    build_closeout_preflight,
    closeout_and_archive,
    project_export_response,
)
from .collaboration_services import (
    assign_collaborator,
    change_collaborator_role,
    remove_collaborator,
    search_eligible_teachers,
    transfer_ownership,
)
from .legacy_link_services import resolve_legacy_project_link
from .material_services import (
    change_project_material_visibility,
    create_project_material,
    project_material_download_response,
    project_material_queryset_for,
)
from .models import (
    DeliverableRevision,
    ProjectMaterial,
    ProjectMembership,
    ResearchProject,
)
from .serializers import (
    CollaboratorCreateSerializer,
    CollaboratorUpdateSerializer,
    MembershipCreateSerializer,
    OwnershipTransferResultSerializer,
    OwnershipTransferSerializer,
    ProjectCreateSerializer,
    ProjectDashboardSerializer,
    ProjectMaterialCreateSerializer,
    ProjectMaterialSerializer,
    ProjectMaterialVisibilitySerializer,
    ProjectMembershipSerializer,
    ProjectSerializer,
    ProjectUpdateSerializer,
)
from .services import ProjectService, can_create_projects, project_event_feed, projects_visible_to


@extend_schema_view(
    list=extend_schema(
        parameters=[
            OpenApiParameter("q", str, OpenApiParameter.QUERY),
            OpenApiParameter("status", str, OpenApiParameter.QUERY),
        ],
        responses={
            200: ProjectSerializer(many=True),
            401: OpenApiResponse(description="Authentication required"),
        },
    ),
    create=extend_schema(
        request=ProjectCreateSerializer,
        responses={
            201: ProjectSerializer,
            400: OpenApiResponse(description="Project validation failed"),
            401: OpenApiResponse(description="Authentication required"),
            403: OpenApiResponse(description="Project creation forbidden"),
        },
    ),
    retrieve=extend_schema(
        parameters=[OpenApiParameter("sinceEventId", str, OpenApiParameter.QUERY)],
        responses={
            200: ProjectDashboardSerializer,
            401: OpenApiResponse(description="Authentication required"),
            403: OpenApiResponse(description="Project access forbidden"),
            404: OpenApiResponse(description="Project not found"),
        },
    ),
)
class ProjectViewSet(
    mixins.CreateModelMixin,
    mixins.ListModelMixin,
    mixins.RetrieveModelMixin,
    mixins.UpdateModelMixin,
    mixins.DestroyModelMixin,
    viewsets.GenericViewSet,
):
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        return projects_visible_to(self.request.user).prefetch_related("memberships")

    def get_serializer_class(self):
        if self.action == "create":
            return ProjectCreateSerializer
        if self.action in {"update", "partial_update"}:
            return ProjectUpdateSerializer
        if self.action == "retrieve":
            return ProjectDashboardSerializer
        return ProjectSerializer

    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        try:
            project = serializer.save()
        except DjangoPermissionDenied as exc:
            raise PermissionDenied(str(exc)) from exc
        except DjangoValidationError as exc:
            raise ValidationError({"message": exc.messages[0]}) from exc
        return Response(
            ProjectSerializer(project, context={"request": request}).data,
            status=status.HTTP_201_CREATED,
        )

    def list(self, request, *args, **kwargs):
        queryset = self.filter_queryset(self.get_queryset())
        status_filter = request.query_params.get("status")
        query = request.query_params.get("q")
        if status_filter:
            queryset = queryset.filter(status=status_filter)
        if query:
            queryset = queryset.filter(title__icontains=query)
        page = self.paginate_queryset(queryset)
        target = page if page is not None else queryset
        serializer = self.get_serializer(target, many=True)
        capabilities = {"canCreateProject": can_create_projects(request.user)}
        if page is not None:
            response = self.get_paginated_response(serializer.data)
            response.data["capabilities"] = capabilities
            return response
        return Response({"results": serializer.data, "capabilities": capabilities})

    def perform_update(self, serializer):
        project = ProjectService(self.request.user).update_project(
            self.get_object(), **serializer.validated_data
        )
        serializer.instance = project

    def destroy(self, request, *args, **kwargs):
        try:
            ProjectService(request.user).delete_project(self.get_object())
        except DjangoPermissionDenied as exc:
            raise PermissionDenied(str(exc)) from exc
        except DjangoValidationError as exc:
            raise ValidationError({"message": exc.messages[0]}) from exc
        return Response(status=status.HTTP_204_NO_CONTENT)

    @extend_schema(
        methods=["POST"],
        request=MembershipCreateSerializer,
        responses={
            201: ProjectMembershipSerializer,
            400: OpenApiResponse(description="Membership validation failed"),
            403: OpenApiResponse(description="Membership change forbidden"),
            409: OpenApiResponse(description="Duplicate or stale membership"),
        },
    )
    @extend_schema(
        methods=["GET"],
        responses={
            200: ProjectMembershipSerializer(many=True),
            403: OpenApiResponse(description="Membership access forbidden"),
        },
    )
    @action(detail=True, methods=["get", "post"], url_path="members")
    def members(self, request, pk=None):
        if request.method == "GET":
            project = self.get_object()
            memberships = project.memberships.select_related("user").order_by(
                "status", "role", "user__email"
            )
            return Response(ProjectMembershipSerializer(memberships, many=True).data)

        project = self.get_object()
        if "studentId" in request.data:
            serializer = MembershipCreateSerializer(data=request.data)
            serializer.is_valid(raise_exception=True)
            try:
                membership = ProjectService(request.user).add_student_member(
                    project, student_id=serializer.validated_data["studentId"]
                )
            except DjangoPermissionDenied as exc:
                raise PermissionDenied(str(exc)) from exc
            except DjangoValidationError as exc:
                raise ValidationError({"message": exc.messages[0]}) from exc
        else:
            membership = ProjectService(request.user).add_member(
                project, user_id=request.data["user_id"], role=request.data["role"]
            )
        return Response(
            ProjectMembershipSerializer(membership).data, status=status.HTTP_201_CREATED
        )

    @action(detail=True, methods=["get", "post"], url_path="collaborators")
    def collaborators(self, request, pk=None):
        project = self.get_object()
        if request.method == "GET":
            memberships = project.memberships.select_related("user").filter(
                role__in=[
                    ProjectMembership.Role.ADVISOR,
                    ProjectMembership.Role.CO_ADVISOR,
                    ProjectMembership.Role.REVIEWER,
                    ProjectMembership.Role.OBSERVER,
                ]
            )
            return Response({"results": ProjectMembershipSerializer(memberships, many=True).data})
        serializer = CollaboratorCreateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        user = get_object_or_404(get_user_model(), pk=serializer.validated_data["userId"])
        try:
            membership = assign_collaborator(
                actor=request.user,
                project=project,
                user=user,
                role=serializer.validated_data["role"],
                reason=serializer.validated_data.get("reason", ""),
            )
        except DjangoPermissionDenied as exc:
            raise PermissionDenied(str(exc)) from exc
        except DjangoValidationError as exc:
            raise ValidationError({"message": exc.messages[0]}) from exc
        return Response(
            ProjectMembershipSerializer(membership).data,
            status=status.HTTP_201_CREATED,
        )

    @action(
        detail=True,
        methods=["patch", "delete"],
        url_path="collaborators/(?P<membership_id>[^/.]+)",
    )
    def collaborator_detail(self, request, pk=None, membership_id=None):
        project = self.get_object()
        membership = get_object_or_404(ProjectMembership, project=project, pk=membership_id)
        try:
            if request.method == "PATCH":
                serializer = CollaboratorUpdateSerializer(data=request.data)
                serializer.is_valid(raise_exception=True)
                membership = change_collaborator_role(
                    actor=request.user,
                    membership=membership,
                    role=serializer.validated_data["role"],
                    expected_version=serializer.validated_data["expectedVersion"],
                    reason=serializer.validated_data.get("reason", ""),
                )
                return Response(ProjectMembershipSerializer(membership).data)
            expected_version = request.query_params.get("expectedVersion")
            if membership.role == ProjectMembership.Role.STUDENT and not expected_version:
                ProjectService(request.user).remove_member(membership)
                return Response(status=status.HTTP_204_NO_CONTENT)
            if not expected_version:
                raise ValidationError({"expectedVersion": "This parameter is required."})
            remove_collaborator(
                actor=request.user,
                membership=membership,
                expected_version=int(expected_version),
                reason=request.query_params.get("reason", ""),
            )
        except DjangoPermissionDenied as exc:
            raise PermissionDenied(str(exc)) from exc
        except DjangoValidationError as exc:
            raise ValidationError({"message": exc.messages[0]}) from exc
        return Response(status=status.HTTP_204_NO_CONTENT)

    @extend_schema(
        methods=["POST"],
        request=OwnershipTransferSerializer,
        responses={
            200: OwnershipTransferResultSerializer,
            400: OpenApiResponse(description="Validation failed"),
            403: OpenApiResponse(description="Transfer forbidden"),
            409: OpenApiResponse(description="Version conflict"),
        },
    )
    @action(detail=True, methods=["post"], url_path="ownership-transfer")
    def ownership_transfer(self, request, pk=None):
        project = self.get_object()
        serializer = OwnershipTransferSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        new_advisor = get_object_or_404(
            get_user_model(), pk=serializer.validated_data["newAdvisorId"]
        )
        try:
            transfer = transfer_ownership(
                actor=request.user,
                project=project,
                new_advisor=new_advisor,
                expected_version=serializer.validated_data["expectedVersion"],
                previous_advisor_result=serializer.validated_data["previousAdvisorResult"],
                reason=serializer.validated_data.get("reason", ""),
                idempotency_key=serializer.validated_data.get("idempotencyKey", ""),
            )
        except DjangoPermissionDenied as exc:
            raise PermissionDenied(str(exc)) from exc
        except DjangoValidationError as exc:
            raise ValidationError({"message": exc.messages[0]}) from exc
        return Response(OwnershipTransferResultSerializer(transfer).data)

    @extend_schema(
        methods=["POST"],
        request=OwnershipTransferSerializer,
        responses={
            200: OwnershipTransferResultSerializer,
            400: OpenApiResponse(description="Validation failed"),
            403: OpenApiResponse(description="Resolution forbidden"),
            409: OpenApiResponse(description="Version conflict"),
        },
    )
    @action(detail=True, methods=["post"], url_path="governance-hold/resolve")
    def resolve_governance_hold(self, request, pk=None):
        return self.ownership_transfer(request, pk=pk)

    @extend_schema(
        methods=["GET"],
        parameters=[
            OpenApiParameter("reviewerId", int, OpenApiParameter.QUERY),
            OpenApiParameter("targetType", str, OpenApiParameter.QUERY),
            OpenApiParameter("status", str, OpenApiParameter.QUERY),
        ],
        responses={
            200: SubmissionReviewAssignmentSerializer(many=True),
            403: OpenApiResponse(description="Assignment access forbidden"),
        },
    )
    @extend_schema(
        methods=["POST"],
        request=SubmissionReviewAssignmentSerializer,
        responses={
            201: SubmissionReviewAssignmentSerializer,
            400: OpenApiResponse(description="Validation failed"),
            403: OpenApiResponse(description="Assignment forbidden"),
            409: OpenApiResponse(description="Assignment conflict"),
        },
    )
    @action(detail=True, methods=["get", "post"], url_path="review-assignments")
    def review_assignments(self, request, pk=None):
        project = self.get_object()
        if request.method == "GET":
            assignments = project.review_assignments.select_related("reviewer_membership__user")
            capabilities = project_capabilities(request.user, project)
            if not (
                capabilities["canAssignReviews"]
                or capabilities["canViewExecutionOperations"]
            ):
                assignments = assignments.filter(
                    reviewer_membership__user=request.user
                )
            return Response(
                {"results": SubmissionReviewAssignmentSerializer(assignments, many=True).data}
            )
        serializer = SubmissionReviewAssignmentSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        membership = get_object_or_404(
            ProjectMembership,
            project=project,
            pk=serializer.validated_data["reviewer_membership_id"],
        )
        targets = [
            (
                serializer.validated_data.get("weekly_report_id"),
                WeeklyProgressReport,
            ),
            (
                serializer.validated_data.get("writing_version_id"),
                WritingVersion,
            ),
            (
                serializer.validated_data.get("draft_version_id"),
                DraftVersion,
            ),
            (
                serializer.validated_data.get("deliverable_revision_id"),
                DeliverableRevision,
            ),
        ]
        selected = [(target_id, model) for target_id, model in targets if target_id]
        if len(selected) != 1:
            raise ValidationError({"message": "Select exactly one review target."})
        target_id, model = selected[0]
        target = get_object_or_404(model, pk=target_id)
        try:
            assignment = assign_reviewer(
                actor=request.user,
                project=project,
                reviewer_membership=membership,
                target=target,
            )
        except DjangoPermissionDenied as exc:
            raise PermissionDenied(str(exc)) from exc
        except DjangoValidationError as exc:
            raise ValidationError({"message": exc.messages[0]}) from exc
        return Response(
            SubmissionReviewAssignmentSerializer(assignment).data,
            status=status.HTTP_201_CREATED,
        )

    @extend_schema(
        methods=["DELETE"],
        parameters=[
            OpenApiParameter(
                "expectedVersion",
                int,
                OpenApiParameter.QUERY,
                required=True,
            )
        ],
        responses={
            204: OpenApiResponse(description="Assignment removed"),
            403: OpenApiResponse(description="Assignment removal forbidden"),
            409: OpenApiResponse(description="Version conflict"),
        },
    )
    @action(
        detail=True,
        methods=["delete"],
        url_path="review-assignments/(?P<assignment_id>[^/.]+)",
    )
    def review_assignment_detail(self, request, pk=None, assignment_id=None):
        project = self.get_object()
        assignment = get_object_or_404(
            SubmissionReviewAssignment, project=project, pk=assignment_id
        )
        try:
            remove_review_assignment(
                actor=request.user,
                assignment=assignment,
                expected_version=int(request.query_params.get("expectedVersion", 0)),
            )
        except DjangoPermissionDenied as exc:
            raise PermissionDenied(str(exc)) from exc
        except DjangoValidationError as exc:
            raise ValidationError({"message": exc.messages[0]}) from exc
        return Response(status=status.HTTP_204_NO_CONTENT)

    @action(detail=True, methods=["post"], url_path="members/(?P<membership_id>[^/.]+)/remove")
    def remove_member(self, request, pk=None, membership_id=None):
        project = self.get_object()
        membership = get_object_or_404(ProjectMembership, project=project, pk=membership_id)
        try:
            membership = ProjectService(request.user).remove_member(membership)
        except DjangoPermissionDenied as exc:
            raise PermissionDenied(str(exc)) from exc
        except DjangoValidationError as exc:
            raise ValidationError({"message": exc.messages[0]}) from exc
        return Response(ProjectMembershipSerializer(membership).data)

    @extend_schema(
        methods=["PATCH"],
        request=CollaboratorUpdateSerializer,
        responses={
            200: ProjectMembershipSerializer,
            400: OpenApiResponse(description="Validation failed"),
            403: OpenApiResponse(description="Membership change forbidden"),
            404: OpenApiResponse(description="Membership not found"),
            409: OpenApiResponse(description="Version conflict"),
        },
    )
    @extend_schema(
        methods=["DELETE"],
        parameters=[
            OpenApiParameter(
                "expectedVersion",
                int,
                OpenApiParameter.QUERY,
                required=True,
            ),
            OpenApiParameter("reason", str, OpenApiParameter.QUERY),
        ],
        responses={
            204: OpenApiResponse(description="Membership removed"),
            400: OpenApiResponse(description="Validation failed"),
            403: OpenApiResponse(description="Membership removal forbidden"),
            404: OpenApiResponse(description="Membership not found"),
            409: OpenApiResponse(description="Version conflict"),
        },
    )
    @action(
        detail=True,
        methods=["patch", "delete"],
        url_path="members/(?P<membership_id>[^/.]+)",
    )
    def delete_member(self, request, pk=None, membership_id=None):
        project = self.get_object()
        membership = get_object_or_404(ProjectMembership, project=project, pk=membership_id)
        try:
            if request.method == "PATCH":
                serializer = CollaboratorUpdateSerializer(data=request.data)
                serializer.is_valid(raise_exception=True)
                membership = change_collaborator_role(
                    actor=request.user,
                    membership=membership,
                    role=serializer.validated_data["role"],
                    expected_version=serializer.validated_data["expectedVersion"],
                    reason=serializer.validated_data.get("reason", ""),
                )
                return Response(ProjectMembershipSerializer(membership).data)
            expected_version = request.query_params.get("expectedVersion")
            if membership.role == ProjectMembership.Role.STUDENT and not expected_version:
                ProjectService(request.user).remove_member(membership)
                return Response(status=status.HTTP_204_NO_CONTENT)
            if not expected_version:
                raise ValidationError({"expectedVersion": "This parameter is required."})
            remove_collaborator(
                actor=request.user,
                membership=membership,
                expected_version=int(expected_version),
                reason=request.query_params.get("reason", ""),
            )
        except DjangoPermissionDenied as exc:
            raise PermissionDenied(str(exc)) from exc
        except DjangoValidationError as exc:
            raise ValidationError({"message": exc.messages[0]}) from exc
        return Response(status=status.HTTP_204_NO_CONTENT)

    @extend_schema(
        methods=["GET"],
        responses={
            200: ProjectCloseoutPreflightSerializer,
            403: OpenApiResponse(description="Project access forbidden"),
        },
    )
    @action(detail=True, methods=["get"], url_path="closeout")
    def closeout(self, request, pk=None):
        try:
            payload = build_closeout_preflight(user=request.user, project=self.get_object())
        except DjangoPermissionDenied as exc:
            raise PermissionDenied(str(exc)) from exc
        return Response(ProjectCloseoutPreflightSerializer(payload).data)

    @extend_schema(
        methods=["POST"],
        request=CloseoutDispositionSerializer,
        responses={
            200: ProjectCloseoutResultSerializer,
            400: OpenApiResponse(description="Closeout items remain unresolved"),
            403: OpenApiResponse(description="Project archival forbidden"),
        },
    )
    @action(detail=True, methods=["post"])
    def archive(self, request, pk=None):
        serializer = CloseoutDispositionSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        try:
            record = closeout_and_archive(
                actor=request.user,
                project=self.get_object(),
                dispositions=serializer.validated_data,
            )
        except DjangoPermissionDenied as exc:
            raise PermissionDenied(str(exc)) from exc
        except DjangoValidationError as exc:
            detail = exc.message_dict if hasattr(exc, "message_dict") else {"message": exc.messages}
            raise ValidationError(detail) from exc
        return Response(
            ProjectCloseoutResultSerializer(
                {
                    "projectId": record.project_id,
                    "status": record.project.status,
                    "archiveVersion": record.archive_version,
                    "archivedAt": record.archived_at,
                    "checklist": record.checklist,
                }
            ).data
        )

    @extend_schema(
        methods=["GET"],
        responses={
            (200, "application/zip"): OpenApiResponse(description="Project closeout package"),
            403: OpenApiResponse(description="Project export forbidden"),
        },
    )
    @action(detail=True, methods=["get"], url_path="export")
    def export(self, request, pk=None):
        try:
            return project_export_response(actor=request.user, project=self.get_object())
        except DjangoPermissionDenied as exc:
            raise PermissionDenied(str(exc)) from exc

    @action(detail=True, methods=["post"])
    def reopen(self, request, pk=None):
        project = ProjectService(request.user).reopen_project(self.get_object())
        return Response(ProjectSerializer(project, context={"request": request}).data)

    @extend_schema(
        methods=["GET"],
        parameters=[
            OpenApiParameter("since", str, OpenApiParameter.QUERY),
            OpenApiParameter("limit", int, OpenApiParameter.QUERY),
        ],
        responses={200: OpenApiResponse(description="Project event feed")},
    )
    @action(detail=True, methods=["get"], url_path="events")
    def events(self, request, pk=None):
        project = self.get_object()
        limit = request.query_params.get("limit", "50")
        try:
            bounded_limit = int(limit)
        except ValueError as exc:
            raise ValidationError({"limit": "Limit must be an integer"}) from exc
        events = project_event_feed(
            project,
            after=request.query_params.get("since") or request.query_params.get("after"),
            limit=bounded_limit,
        )
        return Response(
            {
                "results": events,
                "latestEventId": events[0]["id"] if events else None,
                "generatedAt": timezone.now(),
            }
        )

    @extend_schema(
        methods=["GET"],
        parameters=[
            OpenApiParameter("type", str, OpenApiParameter.QUERY),
            OpenApiParameter("visibility", str, OpenApiParameter.QUERY),
            OpenApiParameter("q", str, OpenApiParameter.QUERY),
        ],
        responses={
            200: ProjectMaterialSerializer(many=True),
            403: OpenApiResponse(description="Project material access forbidden"),
        },
    )
    @extend_schema(
        methods=["POST"],
        request={"multipart/form-data": ProjectMaterialCreateSerializer},
        responses={201: ProjectMaterialSerializer},
    )
    @action(detail=True, methods=["get", "post"], url_path="materials")
    def materials(self, request, pk=None):
        project = self.get_object()
        if request.method == "GET":
            queryset = project_material_queryset_for(request.user, project)
            material_type = request.query_params.get("type")
            visibility = request.query_params.get("visibility")
            query = request.query_params.get("q") or request.query_params.get("search")
            if material_type:
                queryset = queryset.filter(material_type=material_type)
            if visibility:
                queryset = queryset.filter(visibility_state=visibility)
            if query:
                matching_ids = [
                    material.id
                    for material in queryset
                    if query.casefold()
                    in ProjectMaterialSerializer(material, context={"request": request})
                    .data.get("displayName", "")
                    .casefold()
                ]
                queryset = queryset.filter(id__in=matching_ids)
            return Response(
                {
                    "count": queryset.count(),
                    "results": ProjectMaterialSerializer(
                        queryset, many=True, context={"request": request}
                    ).data,
                }
            )

        serializer = ProjectMaterialCreateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        try:
            material = create_project_material(
                user=request.user,
                project=project,
                **serializer.validated_data,
            )
        except DjangoPermissionDenied as exc:
            raise PermissionDenied(str(exc)) from exc
        except DjangoValidationError as exc:
            raise ValidationError({"message": exc.messages[0]}) from exc
        return Response(
            ProjectMaterialSerializer(material, context={"request": request}).data,
            status=status.HTTP_201_CREATED,
        )

    @extend_schema(
        request=ProjectMaterialVisibilitySerializer,
        responses={
            200: ProjectMaterialSerializer,
            403: OpenApiResponse(description="Visibility change forbidden"),
        },
    )
    @action(
        detail=True,
        methods=["patch"],
        url_path="materials/(?P<material_id>[^/.]+)/visibility",
    )
    def material_visibility(self, request, pk=None, material_id=None):
        project = self.get_object()
        material = get_object_or_404(ProjectMaterial, source_project=project, pk=material_id)
        serializer = ProjectMaterialVisibilitySerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        try:
            material = change_project_material_visibility(
                user=request.user,
                material=material,
                **serializer.validated_data,
            )
        except DjangoPermissionDenied as exc:
            raise PermissionDenied(str(exc)) from exc
        except DjangoValidationError as exc:
            raise ValidationError({"message": exc.messages[0]}) from exc
        return Response(ProjectMaterialSerializer(material, context={"request": request}).data)

    @extend_schema(
        methods=["POST"],
        responses={
            200: OpenApiResponse(description="Project material file download"),
            401: OpenApiResponse(description="Authentication required"),
            403: OpenApiResponse(description="Download forbidden"),
            404: OpenApiResponse(description="Project material not found"),
            410: OpenApiResponse(description="Project material unavailable"),
        },
    )
    @action(
        detail=True,
        methods=["get", "post"],
        url_path="materials/(?P<material_id>[^/.]+)/download",
    )
    def material_download(self, request, pk=None, material_id=None):
        project = self.get_object()
        material = get_object_or_404(ProjectMaterial, source_project=project, pk=material_id)
        try:
            return project_material_download_response(request.user, material)
        except (DjangoPermissionDenied, PermissionError) as exc:
            raise PermissionDenied(str(exc)) from exc
        except DownloadUnavailable as exc:
            return Response({"message": str(exc)}, status=status.HTTP_410_GONE)


class LegacyBoundaryLinkView(views.APIView):
    permission_classes = [IsAuthenticated]

    @extend_schema(
        request={
            "application/json": {
                "type": "object",
                "properties": {"path": {"type": "string"}},
            }
        },
        responses={200: OpenApiResponse(description="Legacy boundary resolution")},
    )
    def post(self, request):
        path_value = str(request.data.get("path", ""))
        match = re.fullmatch(
            r"/projects/(?P<project_id>\d+)/(?P<section>papers|code|documents|writing)/?",
            path_value,
        )
        if not match:
            return Response(
                {
                    "mode": "guidance",
                    "targetPath": "",
                    "message": "This link no longer maps to a shared workspace section.",
                },
                status=status.HTTP_404_NOT_FOUND,
            )
        project = get_object_or_404(ResearchProject, pk=match.group("project_id"))
        resolution = resolve_legacy_project_link(
            user=request.user,
            project=project,
            section=match.group("section"),
        )
        return Response(
            {
                "mode": "denied" if resolution.outcome == "denied" else resolution.outcome,
                "targetPath": resolution.target_url,
                "message": resolution.message,
            },
            status=resolution.status_code,
        )


class EligibleTeacherSearchView(views.APIView):
    permission_classes = [IsAuthenticated]

    @extend_schema(
        parameters=[
            OpenApiParameter("q", str, OpenApiParameter.QUERY),
            OpenApiParameter("projectId", int, OpenApiParameter.QUERY),
            OpenApiParameter("role", str, OpenApiParameter.QUERY),
            OpenApiParameter("limit", int, OpenApiParameter.QUERY),
        ],
        responses={
            200: OpenApiResponse(description="Eligible teacher options"),
            401: OpenApiResponse(description="Authentication required"),
            403: OpenApiResponse(description="Teacher search forbidden"),
        },
    )
    def get(self, request):
        project = None
        if request.query_params.get("projectId"):
            project = get_object_or_404(
                projects_visible_to(request.user),
                pk=request.query_params["projectId"],
            )
        teachers = search_eligible_teachers(
            actor=request.user,
            query=request.query_params.get("q", ""),
            project=project,
            limit=int(request.query_params.get("limit", 25)),
        )
        return Response(
            {
                "results": [
                    {
                        "id": teacher.id,
                        "name": teacher.name,
                        "nickname": teacher.nickname,
                        "email": teacher.email,
                        "label": teacher.nickname or teacher.name or teacher.email,
                    }
                    for teacher in teachers
                ]
            }
        )
