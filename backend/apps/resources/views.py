from django.core.exceptions import ValidationError as DjangoValidationError
from django.db.models import Count, Q, Sum
from django.shortcuts import get_object_or_404
from django.utils import timezone
from django.utils.dateparse import parse_datetime
from drf_spectacular.utils import OpenApiParameter, OpenApiResponse, extend_schema
from rest_framework import mixins, status, viewsets
from rest_framework.decorators import action
from rest_framework.exceptions import PermissionDenied, ValidationError
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from apps.common.search import apply_text_search
from apps.projects.models import ResearchProject

from .models import (
    Booking,
    ConsumableStockTransaction,
    ResourceItem,
    ResourceMaintenanceRecord,
    ResourceType,
    ResourceUseSubmission,
)
from .serializers import (
    BookingDecisionSerializer,
    BookingSerializer,
    ConsumableStockTransactionCreateSerializer,
    ConsumableStockTransactionSerializer,
    LaboratoryResourceSerializer,
    ResourceCreateSerializer,
    ResourceItemSerializer,
    ResourceMaintenanceCreateSerializer,
    ResourceMaintenanceSerializer,
    ResourceMaintenanceUpdateSerializer,
    ResourceTypeSerializer,
    ResourceUpdateSerializer,
    ResourceUseSubmissionCreateSerializer,
    ResourceUseSubmissionSerializer,
    ResourceUseSubmissionUpdateSerializer,
)
from .services import (
    BookingService,
    ResourceConflict,
    ResourceInventoryService,
    ResourceOperationsService,
    current_use_periods_by_resource,
    reconcile_completed_bookings,
    reconcile_resource_operation_alerts,
    record_booking_conflict,
    resource_status_from_contract,
)


class ResourceTypeViewSet(
    mixins.CreateModelMixin,
    mixins.ListModelMixin,
    mixins.UpdateModelMixin,
    viewsets.GenericViewSet,
):
    serializer_class = ResourceTypeSerializer
    permission_classes = [IsAuthenticated]
    queryset = ResourceType.objects.all()

    def get_queryset(self):
        queryset = ResourceType.objects.all()
        queryset = apply_text_search(
            queryset, self.request.query_params.get("search"), ["name", "description"]
        )
        status_filter = self.request.query_params.get("status")
        if status_filter:
            queryset = queryset.filter(status=status_filter)
        return queryset

    def perform_create(self, serializer):
        try:
            ResourceInventoryService(self.request.user).require_manager()
        except PermissionError as exc:
            raise PermissionDenied(str(exc)) from exc
        resource_type = serializer.save()
        resource_type.full_clean()

    def perform_update(self, serializer):
        try:
            ResourceInventoryService(self.request.user).require_manager()
        except PermissionError as exc:
            raise PermissionDenied(str(exc)) from exc
        resource_type = serializer.save()
        resource_type.full_clean()


class ResourceItemViewSet(mixins.ListModelMixin, viewsets.GenericViewSet):
    serializer_class = ResourceItemSerializer
    permission_classes = [IsAuthenticated]
    queryset = ResourceItem.objects.select_related("resource_type")

    def get_queryset(self):
        queryset = ResourceItem.objects.select_related("resource_type")
        queryset = apply_text_search(
            queryset,
            self.request.query_params.get("search"),
            ["name", "description", "location", "resource_type__name"],
        )
        status_filter = self.request.query_params.get("status")
        if status_filter:
            queryset = queryset.filter(status=status_filter)
        type_filter = self.request.query_params.get("resource_type_id")
        if type_filter:
            queryset = queryset.filter(resource_type_id=type_filter)
        return queryset

    @action(detail=False, methods=["get"], url_path="availability")
    def availability(self, request):
        starts_at = parse_datetime(request.query_params.get("starts_at", ""))
        ends_at = parse_datetime(request.query_params.get("ends_at", ""))
        queryset = self.get_queryset().filter(kind=ResourceItem.Kind.EQUIPMENT)
        if not starts_at or not ends_at or ends_at <= starts_at:
            raise ValidationError("Availability requires a valid starts_at and ends_at window")
        queryset = queryset.annotate(
            conflicting_booking_count=Count(
                "bookings",
                filter=Q(
                    bookings__status__in=[
                        Booking.Status.RESERVED,
                        Booking.Status.CONFIRMED,
                    ],
                    bookings__starts_at__lt=ends_at,
                    bookings__ends_at__gt=starts_at,
                ),
            )
        )
        resources = list(queryset)
        for resource in resources:
            resource.available = (
                resource.status == ResourceItem.Status.AVAILABLE
                and resource.conflicting_booking_count == 0
            )
        return Response(ResourceItemSerializer(resources, many=True).data)


class StandaloneBookingViewSet(viewsets.ModelViewSet):
    serializer_class = BookingSerializer
    permission_classes = [IsAuthenticated]
    http_method_names = ["get", "post", "patch", "head", "options"]

    def get_queryset(self):
        queryset = Booking.objects.select_related("resource_item", "resource_item__resource_type")
        if getattr(self.request.user, "global_role", "") == "student":
            queryset = queryset.filter(requested_by=self.request.user)
        review_queue = self.request.query_params.get("reviewQueue")
        if review_queue in {"true", "1", "yes"}:
            if getattr(self.request.user, "global_role", "") not in {"advisor", "admin"}:
                queryset = queryset.none()
            else:
                queryset = queryset.filter(
                    origin=Booking.Origin.STUDENT_REQUEST,
                    status=Booking.Status.PENDING,
                )
        origin_filter = self.request.query_params.get("origin")
        if origin_filter:
            queryset = queryset.filter(origin=origin_filter)
        queryset = apply_text_search(
            queryset,
            self.request.query_params.get("search"),
            [
                "purpose",
                "resource_item__name",
                "resource_item__location",
                "resource_item__resource_type__name",
            ],
        )
        status_filter = self.request.query_params.get("status")
        if status_filter:
            if status_filter == Booking.Status.RESERVED:
                queryset = queryset.filter(
                    status__in=[Booking.Status.RESERVED, Booking.Status.CONFIRMED]
                )
            else:
                queryset = queryset.filter(status=status_filter)
        resource_item_id = self.request.query_params.get(
            "resourceId"
        ) or self.request.query_params.get("resourceItemId")
        resource_item_id = resource_item_id or self.request.query_params.get("resource_item_id")
        if resource_item_id:
            queryset = queryset.filter(resource_item_id=resource_item_id)
        return queryset

    @extend_schema(
        request=BookingSerializer,
        responses={
            201: BookingSerializer,
            409: OpenApiResponse(description="Booking capacity or version conflict"),
        },
    )
    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        attrs = dict(serializer.validated_data)
        resource_item = get_object_or_404(ResourceItem, pk=attrs.pop("resource_item_id"))
        try:
            booking = BookingService(request.user).create_booking(
                resource_item=resource_item, **attrs
            )
        except ResourceConflict as exc:
            record_booking_conflict(
                actor=request.user,
                resource=resource_item,
                payload=exc.payload,
            )
            return Response(exc.payload, status=status.HTTP_409_CONFLICT)
        except PermissionError as exc:
            raise PermissionDenied(str(exc)) from exc
        except DjangoValidationError as exc:
            raise ValidationError(exc.messages) from exc
        return Response(self.get_serializer(booking).data, status=status.HTTP_201_CREATED)

    def partial_update(self, request, *args, **kwargs):
        booking = self.get_object()
        serializer = self.get_serializer(data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)
        attrs = dict(serializer.validated_data)
        attrs.pop("resource_item_id", None)
        try:
            booking = BookingService(request.user).update_booking(booking, **attrs)
        except ResourceConflict as exc:
            record_booking_conflict(
                actor=request.user,
                resource=booking.resource_item,
                project=booking.project,
                payload=exc.payload,
            )
            return Response(exc.payload, status=status.HTTP_409_CONFLICT)
        except DjangoValidationError as exc:
            raise ValidationError(exc.messages) from exc
        return Response(self.get_serializer(booking).data)

    @action(detail=True, methods=["post"])
    def cancel(self, request, pk=None, **kwargs):
        booking = self.get_object()
        try:
            booking = BookingService(request.user).cancel_booking(booking)
        except ResourceConflict as exc:
            return Response(exc.payload, status=status.HTTP_409_CONFLICT)
        except DjangoValidationError as exc:
            raise ValidationError(exc.messages) from exc
        return Response(BookingSerializer(booking).data)

    @action(detail=True, methods=["post"], url_path="return")
    def return_resource(self, request, pk=None, **kwargs):
        booking = self.get_object()
        try:
            booking = BookingService(request.user).return_booking(booking)
        except ResourceConflict as exc:
            return Response(exc.payload, status=status.HTTP_409_CONFLICT)
        except DjangoValidationError as exc:
            raise ValidationError(exc.messages) from exc
        return Response(BookingSerializer(booking).data)

    def _decide(self, request, approve):
        serializer = BookingDecisionSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        try:
            booking = BookingService(request.user).decide_booking(
                self.get_object(),
                approve=approve,
                decision_note=serializer.validated_data.get("decisionNote", ""),
            )
        except PermissionError as exc:
            raise PermissionDenied(str(exc)) from exc
        except ResourceConflict as exc:
            return Response(exc.payload, status=status.HTTP_409_CONFLICT)
        except DjangoValidationError as exc:
            raise ValidationError(exc.messages) from exc
        return Response(BookingSerializer(booking).data)

    @action(detail=True, methods=["post"])
    def approve(self, request, pk=None, **kwargs):
        return self._decide(request, True)

    @action(detail=True, methods=["post"])
    def reject(self, request, pk=None, **kwargs):
        return self._decide(request, False)


class BookingViewSet(StandaloneBookingViewSet):
    """Deprecated project-shaped adapter; authorization remains resource-scoped."""

    def finalize_response(self, request, response, *args, **kwargs):
        response = super().finalize_response(request, response, *args, **kwargs)
        response["Deprecation"] = "true"
        response["Sunset"] = "Sat, 31 Jan 2027 00:00:00 GMT"
        response["Link"] = '</api/bookings/>; rel="successor-version"'
        return response

    @extend_schema(
        request=BookingSerializer,
        responses={
            201: BookingSerializer,
            409: OpenApiResponse(description="Booking capacity or version conflict"),
        },
    )
    def create(self, request, *args, **kwargs):
        payload = request.data.copy()
        aliases = {
            "resourceItemId": "resourceId",
            "starts_at": "startsAt",
            "ends_at": "endsAt",
        }
        for legacy, canonical in aliases.items():
            if legacy in payload and canonical not in payload:
                payload[canonical] = payload[legacy]
        request._full_data = payload
        response = super().create(request, *args, **kwargs)
        if response.status_code == status.HTTP_201_CREATED:
            Booking.objects.filter(pk=response.data["id"]).update(
                project_id=kwargs.get("project_id")
            )
        return response


class LaboratoryResourceViewSet(
    mixins.CreateModelMixin,
    mixins.ListModelMixin,
    mixins.RetrieveModelMixin,
    mixins.UpdateModelMixin,
    mixins.DestroyModelMixin,
    viewsets.GenericViewSet,
):
    permission_classes = [IsAuthenticated]
    queryset = ResourceItem.objects.select_related("resource_type", "manager")

    def get_serializer_class(self):
        if self.action == "create":
            return ResourceCreateSerializer
        if self.action in {"partial_update", "update"}:
            return ResourceUpdateSerializer
        if self.action == "use_submissions":
            return ResourceUseSubmissionCreateSerializer
        return LaboratoryResourceSerializer

    @extend_schema(
        parameters=[
            OpenApiParameter("q", str, OpenApiParameter.QUERY),
            OpenApiParameter("status", str, OpenApiParameter.QUERY),
        ],
        responses={200: LaboratoryResourceSerializer(many=True)},
    )
    def list(self, request, *args, **kwargs):
        reconcile_completed_bookings()
        reconcile_resource_operation_alerts()
        queryset = self.filter_queryset(self.get_queryset())
        page = self.paginate_queryset(queryset)
        resources = list(page if page is not None else queryset)
        current_periods = current_use_periods_by_resource([resource.id for resource in resources])
        for resource in resources:
            resource.current_use_periods = current_periods.get(resource.id, [])
        serializer = self.get_serializer(resources, many=True)
        if page is not None:
            return self.get_paginated_response(serializer.data)
        return Response({"results": serializer.data})

    def get_queryset(self):
        queryset = self.queryset
        queryset = apply_text_search(
            queryset,
            self.request.query_params.get("q") or self.request.query_params.get("search"),
            ["name", "description", "resource_type__name", "use_instructions"],
        )
        status_filter = self.request.query_params.get("status")
        if status_filter:
            try:
                queryset = queryset.filter(status=resource_status_from_contract(status_filter))
            except DjangoValidationError as exc:
                raise ValidationError(exc.messages) from exc
        elif self.action != "use_submissions":
            queryset = queryset.exclude(status=ResourceItem.Status.RETIRED)
        return queryset

    @action(detail=False, methods=["get"], url_path="availability")
    def availability(self, request):
        observed_at = timezone.now()
        reconcile_completed_bookings(observed_at)
        starts_at = parse_datetime(
            request.query_params.get("startsAt", "") or request.query_params.get("starts_at", "")
        )
        ends_at = parse_datetime(
            request.query_params.get("endsAt", "") or request.query_params.get("ends_at", "")
        )
        if not starts_at or not ends_at or ends_at <= starts_at:
            raise ValidationError("Availability requires a valid time window")
        queryset = (
            self.get_queryset()
            .filter(kind=ResourceItem.Kind.EQUIPMENT)
            .annotate(
                reserved_quantity=Sum(
                    "bookings__quantity",
                    filter=Q(
                        bookings__status__in=[Booking.Status.CONFIRMED, Booking.Status.RESERVED],
                        bookings__starts_at__lt=ends_at,
                        bookings__ends_at__gt=starts_at,
                    ),
                    default=0,
                )
            )
        )
        resources = list(queryset)
        current_periods = current_use_periods_by_resource(
            [resource.id for resource in resources],
            now=observed_at,
        )
        for resource in resources:
            resource.allocated_quantity = resource.reserved_quantity
            resource.available_quantity = max(
                resource.total_quantity - resource.reserved_quantity, 0
            )
            resource.current_use_periods = current_periods.get(resource.id, [])
        serialized = LaboratoryResourceSerializer(resources, many=True).data
        return Response(
            {
                "observedAt": observed_at.isoformat(),
                "freshnessToken": f"{observed_at.timestamp():.6f}:{len(resources)}",
                "results": serialized,
            }
        )

    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        try:
            resource = ResourceInventoryService(request.user).create_resource(
                name=serializer.validated_data["name"],
                resource_type=serializer.validated_data["resourceType"],
                total_quantity=serializer.validated_data["totalQuantity"],
                location=serializer.validated_data.get("location", ""),
                description=serializer.validated_data.get("description", ""),
                use_instructions=serializer.validated_data.get("useInstructions", ""),
                status=serializer.validated_data.get("status", "active"),
                confirmation_policy_override=serializer.validated_data.get(
                    "confirmationPolicyOverride"
                ),
                kind=serializer.validated_data.get("kind", ResourceItem.Kind.EQUIPMENT),
                stock_on_hand=serializer.validated_data.get("stockOnHand", 0),
                reorder_level=serializer.validated_data.get("reorderLevel", 0),
                stock_unit=serializer.validated_data.get("stockUnit", ""),
                unit_cost=serializer.validated_data.get("unitCost", 0),
                calibration_interval_days=serializer.validated_data.get("calibrationIntervalDays"),
                next_calibration_at=serializer.validated_data.get("nextCalibrationAt"),
            )
        except PermissionError as exc:
            raise PermissionDenied(str(exc)) from exc
        except DjangoValidationError as exc:
            raise ValidationError(exc.messages) from exc
        return Response(LaboratoryResourceSerializer(resource).data, status=status.HTTP_201_CREATED)

    def partial_update(self, request, *args, **kwargs):
        resource = self.get_object()
        serializer = self.get_serializer(data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)
        attrs = dict(serializer.validated_data)
        attrs["resource_type"] = attrs.pop("resourceType", None)
        attrs["use_instructions"] = attrs.pop("useInstructions", None)
        if "totalQuantity" in attrs:
            attrs["total_quantity"] = attrs.pop("totalQuantity")
        if "confirmationPolicyOverride" in attrs:
            attrs["confirmation_policy_override"] = attrs.pop("confirmationPolicyOverride")
        for contract_name, model_name in {
            "reorderLevel": "reorder_level",
            "stockUnit": "stock_unit",
            "unitCost": "unit_cost",
            "calibrationIntervalDays": "calibration_interval_days",
            "nextCalibrationAt": "next_calibration_at",
        }.items():
            if contract_name in attrs:
                attrs[model_name] = attrs.pop(contract_name)
        try:
            resource = ResourceInventoryService(request.user).update_resource(resource, **attrs)
        except PermissionError as exc:
            raise PermissionDenied(str(exc)) from exc
        except DjangoValidationError as exc:
            payload = getattr(exc, "message_dict", None)
            if payload and ("code" in payload or "safeMinimum" in payload):
                return Response(
                    _flatten_validation_payload(payload), status=status.HTTP_409_CONFLICT
                )
            raise ValidationError(exc.messages) from exc
        return Response(LaboratoryResourceSerializer(resource).data)

    def destroy(self, request, *args, **kwargs):
        try:
            ResourceInventoryService(request.user).delete_resource(self.get_object())
        except PermissionError as exc:
            raise PermissionDenied(str(exc)) from exc
        except DjangoValidationError as exc:
            payload = getattr(exc, "message_dict", None)
            if payload:
                return Response(
                    _flatten_validation_payload(payload), status=status.HTTP_409_CONFLICT
                )
            raise ValidationError(exc.messages) from exc
        return Response(status=status.HTTP_204_NO_CONTENT)

    @action(detail=True, methods=["post"])
    def retire(self, request, pk=None):
        serializer = ResourceUpdateSerializer(data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)
        resource = self.get_object()
        if serializer.validated_data.get("version") != resource.version:
            return Response(
                {"code": "stale_resource_version", "currentVersion": resource.version},
                status=status.HTTP_409_CONFLICT,
            )
        try:
            resource = ResourceInventoryService(request.user).retire_resource(resource)
        except PermissionError as exc:
            raise PermissionDenied(str(exc)) from exc
        return Response(LaboratoryResourceSerializer(resource).data)

    @extend_schema(
        request=ResourceUseSubmissionCreateSerializer,
        responses={201: ResourceUseSubmissionSerializer},
    )
    @action(detail=True, methods=["post"], url_path="use-submissions")
    def use_submissions(self, request, pk=None):
        resource = self.get_object()
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        try:
            submission = ResourceInventoryService(request.user).create_use_submission(
                resource,
                submission_type=serializer.validated_data["submissionType"],
                details=serializer.validated_data["details"],
            )
        except PermissionError as exc:
            raise PermissionDenied(str(exc)) from exc
        except DjangoValidationError as exc:
            raise ValidationError(exc.messages) from exc
        return Response(
            ResourceUseSubmissionSerializer(submission).data,
            status=status.HTTP_201_CREATED,
        )


class ResourceMaintenanceViewSet(
    mixins.CreateModelMixin,
    mixins.ListModelMixin,
    mixins.UpdateModelMixin,
    viewsets.GenericViewSet,
):
    permission_classes = [IsAuthenticated]
    queryset = ResourceMaintenanceRecord.objects.select_related(
        "resource_item",
        "created_by",
        "completed_by",
    )

    def get_serializer_class(self):
        if self.action == "create":
            return ResourceMaintenanceCreateSerializer
        if self.action in {"partial_update", "update"}:
            return ResourceMaintenanceUpdateSerializer
        return ResourceMaintenanceSerializer

    def get_queryset(self):
        try:
            ResourceInventoryService(self.request.user).require_manager()
        except PermissionError as exc:
            raise PermissionDenied(str(exc)) from exc
        queryset = self.queryset
        resource_id = self.request.query_params.get("resourceId")
        if resource_id:
            queryset = queryset.filter(resource_item_id=resource_id)
        return queryset

    def list(self, request, *args, **kwargs):
        records = self.get_queryset()[:200]
        return Response({"results": ResourceMaintenanceSerializer(records, many=True).data})

    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        values = serializer.validated_data
        try:
            record = ResourceOperationsService(request.user).create_maintenance(
                resource=get_object_or_404(ResourceItem, pk=values["resourceId"]),
                kind=values["kind"],
                title=values["title"],
                scheduled_at=values["scheduledAt"],
                due_at=values.get("dueAt"),
                details=values.get("details", ""),
                provider=values.get("provider", ""),
                takes_offline=values.get("takesOffline", True),
                cost=values.get("cost", 0),
            )
        except PermissionError as exc:
            raise PermissionDenied(str(exc)) from exc
        except DjangoValidationError as exc:
            raise ValidationError(getattr(exc, "message_dict", exc.messages)) from exc
        return Response(
            ResourceMaintenanceSerializer(record).data,
            status=status.HTTP_201_CREATED,
        )

    def partial_update(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)
        try:
            record = ResourceOperationsService(request.user).transition_maintenance(
                self.get_object(),
                status=serializer.validated_data["status"],
                details=serializer.validated_data.get("details"),
            )
        except PermissionError as exc:
            raise PermissionDenied(str(exc)) from exc
        except DjangoValidationError as exc:
            raise ValidationError(getattr(exc, "message_dict", exc.messages)) from exc
        return Response(ResourceMaintenanceSerializer(record).data)


class ConsumableStockTransactionViewSet(
    mixins.CreateModelMixin,
    mixins.ListModelMixin,
    viewsets.GenericViewSet,
):
    permission_classes = [IsAuthenticated]
    queryset = ConsumableStockTransaction.objects.select_related(
        "resource_item",
        "project",
        "recorded_by",
    )

    def get_serializer_class(self):
        if self.action == "create":
            return ConsumableStockTransactionCreateSerializer
        return ConsumableStockTransactionSerializer

    def get_queryset(self):
        try:
            ResourceInventoryService(self.request.user).require_manager()
        except PermissionError as exc:
            raise PermissionDenied(str(exc)) from exc
        queryset = self.queryset
        resource_id = self.request.query_params.get("resourceId")
        if resource_id:
            queryset = queryset.filter(resource_item_id=resource_id)
        return queryset

    def list(self, request, *args, **kwargs):
        transactions = self.get_queryset()[:200]
        return Response(
            {"results": ConsumableStockTransactionSerializer(transactions, many=True).data}
        )

    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        values = serializer.validated_data
        project = None
        if values.get("projectId"):
            project = get_object_or_404(ResearchProject, pk=values["projectId"])
        try:
            transaction_record = ResourceOperationsService(request.user).record_stock_transaction(
                resource=get_object_or_404(ResourceItem, pk=values["resourceId"]),
                project=project,
                kind=values["kind"],
                quantity_delta=values["quantityDelta"],
                unit_cost=values.get("unitCost"),
                note=values.get("note", ""),
            )
        except PermissionError as exc:
            raise PermissionDenied(str(exc)) from exc
        except ResourceConflict as exc:
            return Response(exc.payload, status=status.HTTP_409_CONFLICT)
        except DjangoValidationError as exc:
            raise ValidationError(getattr(exc, "message_dict", exc.messages)) from exc
        return Response(
            ConsumableStockTransactionSerializer(transaction_record).data,
            status=status.HTTP_201_CREATED,
        )


class ResourceUseSubmissionViewSet(
    mixins.ListModelMixin,
    mixins.RetrieveModelMixin,
    mixins.UpdateModelMixin,
    viewsets.GenericViewSet,
):
    serializer_class = ResourceUseSubmissionUpdateSerializer
    permission_classes = [IsAuthenticated]
    queryset = ResourceUseSubmission.objects.select_related("resource_item", "student", "reviewer")

    def get_queryset(self):
        queryset = self.queryset
        if getattr(self.request.user, "global_role", "") == "student":
            queryset = queryset.filter(student=self.request.user)
        return queryset

    def partial_update(self, request, *args, **kwargs):
        submission = self.get_object()
        serializer = self.get_serializer(data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)
        try:
            submission = ResourceInventoryService(request.user).decide_use_submission(
                submission,
                status=serializer.validated_data["status"],
                decision_note=serializer.validated_data.get("decisionNote", ""),
            )
        except PermissionError as exc:
            raise PermissionDenied(str(exc)) from exc
        except DjangoValidationError as exc:
            raise ValidationError(exc.messages) from exc
        return Response(ResourceUseSubmissionSerializer(submission).data)


def _flatten_validation_payload(payload):
    return {
        key: values[0] if isinstance(values, (list, tuple)) and len(values) == 1 else values
        for key, values in payload.items()
    }
