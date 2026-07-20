from django.core.exceptions import PermissionDenied as DjangoPermissionDenied
from django.core.exceptions import ValidationError as DjangoValidationError
from django.db.models import Count, Q
from django.shortcuts import get_object_or_404
from django.utils import timezone
from drf_spectacular.utils import OpenApiParameter, OpenApiResponse, extend_schema
from rest_framework import serializers, status, views
from rest_framework.exceptions import PermissionDenied
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from apps.common.openapi import delete_json_request_body

from .audience_services import audience_options
from .conflict_services import visible_conflicts
from .event_services import schedule_events_visible_to
from .models import ScheduleItem, ScheduleNotificationDispatch
from .permissions import can_manage_group_item, can_publish_group_item
from .projection_services import SOURCE_TYPES, aggregate_calendar_occurrences
from .serializers import (
    ConflictCheckSerializer,
    ScheduleActionSerializer,
    ScheduleCancelSerializer,
    ScheduleCreateSerializer,
    ScheduleItemSerializer,
    ScheduleOccurrenceSerializer,
    SchedulePublishSerializer,
    ScheduleUpdateSerializer,
    schedule_detail,
)
from .services import (
    ScheduleVersionConflict,
    cancel_schedule,
    complete_schedule,
    create_schedule,
    delete_private_schedule,
    publish_schedule,
    update_schedule,
)


def _validation_response(exc):
    if hasattr(exc, "message_dict"):
        return Response(exc.message_dict, status=status.HTTP_400_BAD_REQUEST)
    return Response({"message": "; ".join(exc.messages)}, status=status.HTTP_400_BAD_REQUEST)


def _visible_schedule(user, schedule_id):
    visibility = Q(owner=user) | Q(
        scope=ScheduleItem.Scope.GROUP,
        recipient_grants__recipient=user,
        recipient_grants__valid_until__isnull=True,
    )
    if getattr(user, "is_administrator", False):
        visibility |= Q(scope=ScheduleItem.Scope.GROUP)
    return get_object_or_404(
        ScheduleItem.objects.filter(visibility)
        .select_related("owner", "organizer")
        .prefetch_related("reminders", "audiences")
        .distinct(),
        pk=schedule_id,
    )


def _version_conflict(exc, user):
    return Response(
        {
            "code": "stale_schedule_version",
            "message": str(exc),
            "currentVersion": exc.item.version,
            "current": schedule_detail(exc.item, user),
        },
        status=status.HTTP_409_CONFLICT,
    )


class CalendarPeriodSerializer(serializers.Serializer):
    startsAt = serializers.DateTimeField()
    endsAt = serializers.DateTimeField()
    sources = serializers.CharField(required=False, allow_blank=True)
    cursor = serializers.CharField(required=False)
    limit = serializers.IntegerField(min_value=1, max_value=200, default=100)

    def validate(self, attrs):
        if attrs["endsAt"] <= attrs["startsAt"]:
            raise serializers.ValidationError({"endsAt": "End must be after start."})
        if attrs["endsAt"] - attrs["startsAt"] > timezone.timedelta(days=62):
            raise serializers.ValidationError({"endsAt": "Calendar windows cannot exceed 62 days."})
        raw_sources = attrs.get("sources", "")
        sources = {value for value in raw_sources.split(",") if value}
        invalid = sources - SOURCE_TYPES
        if invalid:
            raise serializers.ValidationError(
                {"sources": f"Unsupported sources: {', '.join(sorted(invalid))}"}
            )
        attrs["source_set"] = sources or SOURCE_TYPES
        return attrs


class CalendarOccurrenceView(views.APIView):
    serializer_class = ScheduleOccurrenceSerializer
    permission_classes = [IsAuthenticated]
    throttle_scope = "calendar"

    @extend_schema(
        parameters=[
            OpenApiParameter("startsAt", str, required=True),
            OpenApiParameter("endsAt", str, required=True),
            OpenApiParameter("sources", str),
            OpenApiParameter("cursor", str),
            OpenApiParameter("limit", int),
        ],
        responses={
            200: ScheduleOccurrenceSerializer(many=True),
            400: OpenApiResponse(description="Invalid period"),
            401: OpenApiResponse(description="Authentication required"),
            429: OpenApiResponse(description="Rate limited"),
        },
    )
    def get(self, request):
        serializer = CalendarPeriodSerializer(data=request.query_params)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data
        results = aggregate_calendar_occurrences(
            request.user, data["startsAt"], data["endsAt"], data["source_set"]
        )
        results = results[:10000]
        return Response(
            {
                "results": ScheduleOccurrenceSerializer(results, many=True).data,
                "nextCursor": None,
                "generatedAt": timezone.now(),
                "latestEventId": "",
            }
        )


class CalendarEventView(views.APIView):
    serializer_class = ScheduleOccurrenceSerializer
    permission_classes = [IsAuthenticated]
    throttle_scope = "calendar"

    @extend_schema(
        parameters=[OpenApiParameter("since", str), OpenApiParameter("limit", int)],
        responses={
            200: ScheduleOccurrenceSerializer(many=True),
            401: OpenApiResponse(description="Authentication required"),
        },
    )
    def get(self, request):
        try:
            limit = min(max(int(request.query_params.get("limit", 50)), 1), 100)
        except ValueError:
            return Response(
                {"limit": ["Enter a valid integer."]}, status=status.HTTP_400_BAD_REQUEST
            )
        events = schedule_events_visible_to(
            request.user, after=request.query_params.get("since"), limit=limit
        )
        latest = events[-1]["cursor"] if events else request.query_params.get("since", "")
        results = [
            {
                "eventId": event["cursor"],
                "eventType": "schedule_changed",
                "scheduleId": event["itemId"],
                "sourceType": "schedule",
                "sourceId": str(event["itemId"]),
                "occurredAt": event["updatedAt"],
            }
            for event in events
        ]
        return Response(
            {"results": results, "latestEventId": latest, "generatedAt": timezone.now()}
        )


class ScheduleCollectionView(views.APIView):
    serializer_class = ScheduleCreateSerializer
    permission_classes = [IsAuthenticated]
    throttle_scope = "calendar"

    @extend_schema(
        request=ScheduleCreateSerializer,
        responses={
            201: ScheduleItemSerializer,
            400: OpenApiResponse(description="Validation failed"),
            403: OpenApiResponse(description="Forbidden"),
            409: OpenApiResponse(description="Confirmation required"),
            429: OpenApiResponse(description="Rate limited"),
        },
    )
    def post(self, request):
        serializer = ScheduleCreateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data
        if data.get("scope") == ScheduleItem.Scope.GROUP and not can_publish_group_item(
            request.user
        ):
            raise PermissionDenied("Only advisors and administrators can publish group schedules.")
        conflicts = visible_conflicts(
            request.user,
            starts_at=data.get("starts_at"),
            ends_at=data.get("ends_at"),
            starts_on=data.get("starts_on"),
            ends_on=data.get("ends_on"),
        )
        if conflicts and not data.get("confirm_conflicts"):
            return Response(
                {
                    "code": "schedule_conflict_confirmation_required",
                    "message": "This schedule overlaps visible work. Confirm to continue.",
                    "conflicts": conflicts,
                },
                status=status.HTTP_409_CONFLICT,
            )
        try:
            item = create_schedule(actor=request.user, data=data)
        except DjangoPermissionDenied as exc:
            raise PermissionDenied(str(exc)) from exc
        except DjangoValidationError as exc:
            return _validation_response(exc)
        item = _visible_schedule(request.user, item.id)
        return Response(schedule_detail(item, request.user), status=status.HTTP_201_CREATED)


class ScheduleDetailView(views.APIView):
    serializer_class = ScheduleItemSerializer
    permission_classes = [IsAuthenticated]
    throttle_scope = "calendar"

    @extend_schema(
        responses={
            200: ScheduleItemSerializer,
            403: OpenApiResponse(description="Forbidden"),
            404: OpenApiResponse(description="Not found"),
        }
    )
    def get(self, request, schedule_id):
        return Response(schedule_detail(_visible_schedule(request.user, schedule_id), request.user))

    @extend_schema(
        request=ScheduleUpdateSerializer,
        responses={
            200: ScheduleItemSerializer,
            400: OpenApiResponse(description="Validation failed"),
            403: OpenApiResponse(description="Forbidden"),
            404: OpenApiResponse(description="Not found"),
            409: OpenApiResponse(description="Version conflict"),
        },
    )
    def patch(self, request, schedule_id):
        item = _visible_schedule(request.user, schedule_id)
        serializer = ScheduleUpdateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data
        data.pop("confirm_conflicts", None)
        data.pop("audience", None)
        try:
            updated = update_schedule(item=item, actor=request.user, **data)
        except ScheduleVersionConflict as exc:
            return _version_conflict(exc, request.user)
        except DjangoPermissionDenied as exc:
            raise PermissionDenied(str(exc)) from exc
        except DjangoValidationError as exc:
            return _validation_response(exc)
        updated = _visible_schedule(request.user, updated.id)
        return Response(schedule_detail(updated, request.user))

    @extend_schema(
        request=ScheduleActionSerializer,
        extensions=delete_json_request_body(
            {
                "type": "object",
                "required": ["expectedVersion", "changeScope", "confirmed"],
                "properties": {
                    "expectedVersion": {"type": "integer", "minimum": 1},
                    "changeScope": {
                        "type": "string",
                        "enum": ["occurrence", "future", "series"],
                    },
                    "occurrenceKey": {"type": "string", "nullable": True},
                    "confirmed": {"type": "boolean", "enum": [True]},
                },
            }
        ),
        responses={
            204: None,
            400: OpenApiResponse(description="Validation failed"),
            403: OpenApiResponse(description="Forbidden"),
            409: OpenApiResponse(description="Version conflict"),
        },
    )
    def delete(self, request, schedule_id):
        item = _visible_schedule(request.user, schedule_id)
        serializer = ScheduleActionSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data
        data.pop("confirmed", None)
        try:
            delete_private_schedule(item=item, actor=request.user, **data)
        except ScheduleVersionConflict as exc:
            return _version_conflict(exc, request.user)
        except DjangoPermissionDenied as exc:
            raise PermissionDenied(str(exc)) from exc
        except DjangoValidationError as exc:
            return _validation_response(exc)
        return Response(status=status.HTTP_204_NO_CONTENT)


class ScheduleCompleteView(views.APIView):
    serializer_class = ScheduleActionSerializer
    permission_classes = [IsAuthenticated]

    def post(self, request, schedule_id):
        item = _visible_schedule(request.user, schedule_id)
        serializer = ScheduleActionSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data
        data.pop("confirmed", None)
        try:
            updated = complete_schedule(item=item, actor=request.user, **data)
        except ScheduleVersionConflict as exc:
            return _version_conflict(exc, request.user)
        except DjangoPermissionDenied as exc:
            raise PermissionDenied(str(exc)) from exc
        except DjangoValidationError as exc:
            return _validation_response(exc)
        updated = _visible_schedule(request.user, updated.id)
        return Response(schedule_detail(updated, request.user))


class ScheduleConflictView(views.APIView):
    serializer_class = ConflictCheckSerializer
    permission_classes = [IsAuthenticated]
    throttle_scope = "calendar"

    @extend_schema(
        request=ConflictCheckSerializer,
        responses={
            200: ScheduleOccurrenceSerializer(many=True),
            400: OpenApiResponse(description="Validation failed"),
        },
    )
    def post(self, request):
        serializer = ConflictCheckSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data
        results = visible_conflicts(
            request.user,
            starts_at=data.get("starts_at"),
            ends_at=data.get("ends_at"),
            starts_on=data.get("starts_on"),
            ends_on=data.get("ends_on"),
            exclude_schedule_id=data.get("schedule_id"),
        )
        return Response({"results": results})


class ScheduleAudienceOptionsView(views.APIView):
    serializer_class = ScheduleItemSerializer
    permission_classes = [IsAuthenticated]
    throttle_scope = "calendar"

    @extend_schema(
        parameters=[
            OpenApiParameter("type", str, required=True),
            OpenApiParameter("q", str),
            OpenApiParameter("cursor", str),
            OpenApiParameter("limit", int),
        ],
        responses={
            200: ScheduleItemSerializer(many=True),
            403: OpenApiResponse(description="Forbidden"),
            429: OpenApiResponse(description="Rate limited"),
        },
    )
    def get(self, request):
        option_type = request.query_params.get("type", "")
        query = request.query_params.get("q", "")[:100]
        try:
            limit = min(max(int(request.query_params.get("limit", 20)), 1), 50)
            results = audience_options(request.user, option_type, query, limit)
        except ValueError:
            return Response({"limit": ["Enter a valid integer."]}, status=400)
        except DjangoPermissionDenied as exc:
            raise PermissionDenied(str(exc)) from exc
        except DjangoValidationError as exc:
            return _validation_response(exc)
        return Response({"results": results, "nextCursor": None})


class SchedulePublishView(views.APIView):
    serializer_class = SchedulePublishSerializer
    permission_classes = [IsAuthenticated]
    throttle_scope = "calendar"

    @extend_schema(
        request=SchedulePublishSerializer,
        responses={
            200: ScheduleItemSerializer,
            400: OpenApiResponse(description="Validation failed"),
            403: OpenApiResponse(description="Forbidden"),
            409: OpenApiResponse(description="Version conflict"),
        },
    )
    def post(self, request, schedule_id):
        item = _visible_schedule(request.user, schedule_id)
        serializer = SchedulePublishSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data
        data.pop("confirmed", None)
        data.pop("confirm_conflicts", None)
        try:
            updated = publish_schedule(item=item, actor=request.user, **data)
        except ScheduleVersionConflict as exc:
            return _version_conflict(exc, request.user)
        except DjangoPermissionDenied as exc:
            raise PermissionDenied(str(exc)) from exc
        except DjangoValidationError as exc:
            return _validation_response(exc)
        updated = _visible_schedule(request.user, updated.id)
        return Response(schedule_detail(updated, request.user))


class ScheduleCancelView(views.APIView):
    serializer_class = ScheduleCancelSerializer
    permission_classes = [IsAuthenticated]
    throttle_scope = "calendar"

    @extend_schema(
        request=ScheduleCancelSerializer,
        responses={
            200: ScheduleItemSerializer,
            403: OpenApiResponse(description="Forbidden"),
            409: OpenApiResponse(description="Version conflict"),
        },
    )
    def post(self, request, schedule_id):
        item = _visible_schedule(request.user, schedule_id)
        serializer = ScheduleCancelSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data
        data.pop("confirmed", None)
        try:
            updated = cancel_schedule(item=item, actor=request.user, **data)
        except ScheduleVersionConflict as exc:
            return _version_conflict(exc, request.user)
        except DjangoPermissionDenied as exc:
            raise PermissionDenied(str(exc)) from exc
        except DjangoValidationError as exc:
            return _validation_response(exc)
        return Response(schedule_detail(_visible_schedule(request.user, updated.id), request.user))


class ScheduleRevisionView(views.APIView):
    serializer_class = ScheduleItemSerializer
    permission_classes = [IsAuthenticated]

    @extend_schema(
        responses={
            200: ScheduleItemSerializer(many=True),
            403: OpenApiResponse(description="Forbidden"),
        }
    )
    def get(self, request, schedule_id):
        item = _visible_schedule(request.user, schedule_id)
        if item.scope != ScheduleItem.Scope.GROUP:
            raise PermissionDenied("Revision history is available for group schedules.")
        results = [
            {
                "id": revision.id,
                "revisionNumber": revision.revision_number,
                "changeType": revision.change_type,
                "changedFields": revision.changed_fields,
                "effectiveFrom": revision.effective_from,
                "audienceSummary": {
                    "projectCount": revision.audience_summary.get("projectCount", 0),
                    "accountCount": revision.audience_summary.get("accountCount", 0),
                    "resolvedRecipientCount": revision.audience_summary.get(
                        "resolvedRecipientCount", 0
                    ),
                },
                "actor": {
                    "id": revision.actor_id,
                    "name": revision.actor.name,
                    "role": revision.actor.global_role,
                },
                "createdAt": revision.created_at,
            }
            for revision in item.revisions.select_related("actor")
        ]
        return Response({"count": len(results), "results": results})


class ScheduleDeliveryStatusView(views.APIView):
    serializer_class = ScheduleItemSerializer
    permission_classes = [IsAuthenticated]

    @extend_schema(
        responses={
            200: ScheduleItemSerializer,
            403: OpenApiResponse(description="Forbidden"),
        }
    )
    def get(self, request, schedule_id):
        item = _visible_schedule(request.user, schedule_id)
        if not can_manage_group_item(request.user, item):
            raise PermissionDenied("Only the publisher or an administrator can view delivery.")
        dispatches = ScheduleNotificationDispatch.objects.filter(schedule_item=item)
        channels = {}
        for channel in ScheduleNotificationDispatch.Channel.values:
            scoped = dispatches.filter(channel=channel)
            channels[channel] = {
                status_name: scoped.filter(status=status_value).count()
                for status_value, status_name in (
                    (ScheduleNotificationDispatch.Status.CLAIMED, "claimed"),
                    (ScheduleNotificationDispatch.Status.CREATED, "created"),
                    (ScheduleNotificationDispatch.Status.SKIPPED, "skipped"),
                    (ScheduleNotificationDispatch.Status.FAILED, "failed"),
                )
            }
            channels[channel]["total"] = scoped.count()
        failure_codes = [
            {"code": row["failure_code"], "count": row["count"]}
            for row in dispatches.exclude(failure_code="")
            .values("failure_code")
            .annotate(count=Count("id"))
            .order_by("failure_code")
        ]
        return Response(
            {
                "scheduleId": item.id,
                "resolvedRecipients": {
                    "active": item.recipient_grants.filter(valid_until__isnull=True).count(),
                    "removed": item.recipient_grants.filter(valid_until__isnull=False)
                    .values("recipient_id")
                    .distinct()
                    .count(),
                },
                "notifications": {
                    "inAppCreated": channels["in_app"]["created"],
                    "inAppClaimed": channels["in_app"]["claimed"],
                    "emailSent": channels["email"]["created"],
                    "emailQueued": channels["email"]["claimed"],
                    "emailFailed": channels["email"]["failed"],
                    "skipped": channels["in_app"]["skipped"] + channels["email"]["skipped"],
                },
                "deliveryPolicy": {
                    "publication": "in_app",
                    "ordinaryChange": "in_app",
                    "cancellation": "in_app_email",
                    "reminder": "in_app_email",
                },
                "failureCodes": failure_codes,
                "updatedAt": timezone.now(),
            }
        )
