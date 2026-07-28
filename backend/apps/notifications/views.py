from django.conf import settings
from django.db.models import Count
from django.shortcuts import get_object_or_404
from django.utils import timezone
from django.utils.dateparse import parse_datetime
from drf_spectacular.utils import (
    OpenApiParameter,
    OpenApiResponse,
    extend_schema,
    extend_schema_view,
)
from rest_framework import generics, mixins, status, views, viewsets
from rest_framework.exceptions import PermissionDenied, ValidationError
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from apps.common.concurrency import VersionConflict
from apps.common.pagination import bounded_page_size
from apps.projects.access_services import project_capabilities
from apps.projects.services import projects_visible_to

from .models import Notification, NotificationDeliveryAttempt, NotificationReadReceipt
from .outcome_services import acknowledge_notification
from .policy_services import (
    effective_project_policy,
    preference_profile_for,
    update_preference_profile,
    update_project_policy,
)
from .serializers import (
    NotificationOperationsSummarySerializer,
    NotificationPreferenceSerializer,
    NotificationPreferenceWriteSerializer,
    NotificationReadSerializer,
    NotificationSerializer,
    ProjectNotificationPolicySerializer,
    ProjectNotificationPolicyWriteSerializer,
)
from .services import notifications_visible_to

_NOTIFICATION_ERRORS = {
    400: OpenApiResponse(description="Validation error"),
    401: OpenApiResponse(description="Authentication required"),
    403: OpenApiResponse(description="Forbidden"),
    404: OpenApiResponse(description="Not found"),
    409: OpenApiResponse(description="Conflict"),
}


@extend_schema_view(
    get=extend_schema(
        parameters=[
            OpenApiParameter("category", str, OpenApiParameter.QUERY),
            OpenApiParameter("outcome", str, OpenApiParameter.QUERY),
            OpenApiParameter("projectId", int, OpenApiParameter.QUERY),
            OpenApiParameter("createdAfter", str, OpenApiParameter.QUERY),
            OpenApiParameter("unread", bool, OpenApiParameter.QUERY),
            OpenApiParameter("cursor", str, OpenApiParameter.QUERY),
            OpenApiParameter("pageSize", int, OpenApiParameter.QUERY),
        ],
        responses={
            200: NotificationSerializer(many=True),
            401: OpenApiResponse(description="Authentication required"),
        },
    )
)
class NotificationStatusListView(generics.GenericAPIView):
    serializer_class = NotificationSerializer
    permission_classes = [IsAuthenticated]

    def get(self, request):
        queryset = notifications_visible_to(request.user)
        category = request.query_params.get("category")
        outcome = request.query_params.get("outcome")
        project_id = request.query_params.get("projectId")
        created_after = request.query_params.get("createdAfter")
        if category:
            queryset = queryset.filter(category=category)
        if outcome:
            queryset = queryset.filter(outcome_state=outcome)
        if project_id:
            queryset = queryset.filter(project_id=project_id)
        if created_after:
            parsed = parse_datetime(created_after)
            if parsed is None:
                raise ValidationError({"createdAfter": "Enter a valid date-time."})
            queryset = queryset.filter(created_at__gte=parsed)
        unread = request.query_params.get("unread")
        if unread in {"true", "1"}:
            queryset = queryset.filter(viewer_read_at__isnull=True)
        elif unread in {"false", "0"}:
            queryset = queryset.filter(viewer_read_at__isnull=False)
        page_size = bounded_page_size(
            request.query_params.get("pageSize") or request.query_params.get("page_size"),
            maximum=100,
        )
        cursor = request.query_params.get("cursor")
        if cursor:
            try:
                queryset = queryset.filter(pk__lt=int(cursor))
            except ValueError as exc:
                raise ValidationError({"cursor": "Cursor is invalid."}) from exc
        page = list(queryset.order_by("-id")[: page_size + 1])
        has_more = len(page) > page_size
        page = page[:page_size]
        return Response(
            {
                "results": NotificationSerializer(page, many=True).data,
                "nextCursor": str(page[-1].pk) if has_more and page else None,
                "unreadCount": notifications_visible_to(request.user)
                .filter(viewer_read_at__isnull=True)
                .count(),
                "pendingActionCount": notifications_visible_to(request.user)
                .filter(
                    active_follow_up=True,
                    outcome_state=Notification.OutcomeState.PENDING,
                )
                .count(),
            }
        )


class NotificationReadView(views.APIView):
    permission_classes = [IsAuthenticated]

    @extend_schema(
        request=NotificationReadSerializer,
        responses={
            200: OpenApiResponse(description="Visible notifications marked as read"),
            400: _NOTIFICATION_ERRORS[400],
            401: _NOTIFICATION_ERRORS[401],
        },
    )
    def post(self, request):
        serializer = NotificationReadSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        through_id = serializer.validated_data.get("throughId")
        selected_ids = serializer.validated_data.get("notificationIds")
        visible = notifications_visible_to(request.user)
        notification_ids = list(
            visible.filter(
                pk__in=selected_ids
                if selected_ids is not None
                else visible.filter(pk__lte=through_id).values("pk")
            ).values_list("pk", flat=True)
        )
        NotificationReadReceipt.objects.bulk_create(
            [
                NotificationReadReceipt(notification_id=notification_id, viewer=request.user)
                for notification_id in notification_ids
            ],
            ignore_conflicts=True,
        )
        return Response(
            {
                "throughId": through_id,
                "readAt": timezone.now(),
                "visibleCount": len(notification_ids),
                "updatedIds": sorted(notification_ids),
            },
            status=status.HTTP_200_OK,
        )


class ProjectNotificationViewSet(mixins.ListModelMixin, viewsets.GenericViewSet):
    serializer_class = NotificationSerializer
    permission_classes = [IsAuthenticated]

    def get_project(self):
        return get_object_or_404(
            projects_visible_to(self.request.user), pk=self.kwargs["project_id"]
        )

    def get_queryset(self):
        return notifications_visible_to(self.request.user, project=self.get_project())


class NotificationAcknowledgeView(generics.GenericAPIView):
    permission_classes = [IsAuthenticated]
    serializer_class = NotificationSerializer

    @extend_schema(
        request={"application/json": {"type": "object", "properties": {}}},
        responses={200: NotificationSerializer, **_NOTIFICATION_ERRORS},
    )
    def post(self, request, notification_id):
        notification = get_object_or_404(notifications_visible_to(request.user), pk=notification_id)
        acknowledged = acknowledge_notification(notification=notification, actor=request.user)
        acknowledged.viewer_read_at = (
            NotificationReadReceipt.objects.filter(notification=acknowledged, viewer=request.user)
            .values_list("viewed_at", flat=True)
            .first()
        )
        return Response(NotificationSerializer(acknowledged).data)


class NotificationPreferenceView(generics.GenericAPIView):
    permission_classes = [IsAuthenticated]
    serializer_class = NotificationPreferenceSerializer

    @extend_schema(
        responses={
            200: NotificationPreferenceSerializer,
            401: _NOTIFICATION_ERRORS[401],
        }
    )
    def get(self, request):
        return Response(NotificationPreferenceSerializer(preference_profile_for(request.user)).data)

    @extend_schema(
        request=NotificationPreferenceWriteSerializer,
        responses={200: NotificationPreferenceSerializer, **_NOTIFICATION_ERRORS},
    )
    def patch(self, request):
        serializer = NotificationPreferenceWriteSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data
        try:
            profile = update_preference_profile(
                user=request.user,
                expected_version=data["expectedVersion"],
                quiet_hours_enabled=data["quietHoursEnabled"],
                quiet_hours_start=data.get("quietHoursStart"),
                quiet_hours_end=data.get("quietHoursEnd"),
                timezone_name=data["timezone"],
                category_email=data["categoryEmail"],
            )
        except VersionConflict as exc:
            return Response(
                {"code": "version_conflict", "current": exc.current_state},
                status=status.HTTP_409_CONFLICT,
            )
        return Response(NotificationPreferenceSerializer(profile).data)


class ProjectNotificationPolicyView(generics.GenericAPIView):
    permission_classes = [IsAuthenticated]
    serializer_class = ProjectNotificationPolicySerializer

    def _project(self, request, project_id):
        return get_object_or_404(projects_visible_to(request.user), pk=project_id)

    @extend_schema(responses={200: ProjectNotificationPolicySerializer, **_NOTIFICATION_ERRORS})
    def get(self, request, project_id):
        project = self._project(request, project_id)
        effective = effective_project_policy(project)
        return Response(
            {
                "version": effective["version"],
                "reminderLeadMinutes": effective["reminder_lead_minutes"],
                "escalationDelayMinutes": effective["escalation_delay_minutes"],
                "repeatIntervalMinutes": effective["repeat_interval_minutes"],
                "maxReminders": effective["max_reminders"],
                "usesSystemDefaults": effective["uses_system_defaults"],
                "bounds": {
                    "minimumMinutes": settings.GRADSYNC_NOTIFICATION_THRESHOLD_MIN_MINUTES,
                    "maximumMinutes": settings.GRADSYNC_NOTIFICATION_THRESHOLD_MAX_MINUTES,
                },
                "capabilities": {
                    "canEdit": project_capabilities(request.user, project)[
                        "canManageProjectNotificationPolicy"
                    ]
                },
            }
        )

    @extend_schema(
        request=ProjectNotificationPolicyWriteSerializer,
        responses={200: ProjectNotificationPolicySerializer, **_NOTIFICATION_ERRORS},
    )
    def patch(self, request, project_id):
        project = self._project(request, project_id)
        serializer = ProjectNotificationPolicyWriteSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        source = serializer.validated_data
        fields = {}
        if "reminderLeadMinutes" in source:
            fields["reminder_lead_minutes"] = source["reminderLeadMinutes"]
        if "escalationDelayMinutes" in source:
            fields["escalation_delay_minutes"] = source["escalationDelayMinutes"]
        if "repeatIntervalMinutes" in source:
            fields["repeat_interval_minutes"] = source["repeatIntervalMinutes"]
        if "maxReminders" in source:
            fields["max_reminders"] = source["maxReminders"]
        try:
            policy = update_project_policy(
                actor=request.user,
                project=project,
                expected_version=source["expectedVersion"],
                **fields,
            )
        except VersionConflict as exc:
            return Response(
                {"code": "version_conflict", "current": exc.current_state},
                status=status.HTTP_409_CONFLICT,
            )
        payload = ProjectNotificationPolicySerializer(policy).data
        payload["usesSystemDefaults"] = False
        payload["capabilities"] = {"canEdit": True}
        return Response(payload)


class NotificationOperationsSummaryView(generics.GenericAPIView):
    permission_classes = [IsAuthenticated]
    serializer_class = NotificationOperationsSummarySerializer

    @extend_schema(
        parameters=[
            OpenApiParameter("from", str, OpenApiParameter.QUERY, required=True),
            OpenApiParameter("to", str, OpenApiParameter.QUERY, required=True),
        ],
        responses={
            200: NotificationOperationsSummarySerializer,
            **_NOTIFICATION_ERRORS,
        },
    )
    def get(self, request):
        if not request.user.is_administrator:
            raise PermissionDenied("Administrator access is required.")
        start = parse_datetime(request.query_params.get("from", ""))
        end = parse_datetime(request.query_params.get("to", ""))
        if not start or not end or end < start:
            raise ValidationError({"range": "A valid bounded from/to range is required."})
        if end - start > timezone.timedelta(days=31):
            raise ValidationError({"range": "Operations summary cannot exceed 31 days."})
        notifications = Notification.objects.filter(created_at__range=(start, end))
        attempts = NotificationDeliveryAttempt.objects.filter(created_at__range=(start, end))
        return Response(
            {
                "notifications": notifications.count(),
                "pendingFollowUps": notifications.filter(active_follow_up=True).count(),
                "outcomes": list(
                    notifications.values("outcome_state")
                    .annotate(count=Count("id"))
                    .order_by("outcome_state")
                ),
                "deliveryAttempts": list(
                    attempts.values("channel", "state")
                    .annotate(count=Count("id"))
                    .order_by("channel", "state")
                ),
            }
        )
