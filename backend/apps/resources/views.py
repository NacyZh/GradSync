from django.core.exceptions import ValidationError as DjangoValidationError
from django.db.models import Count, Q
from django.shortcuts import get_object_or_404
from django.utils.dateparse import parse_datetime
from rest_framework import mixins, status, viewsets
from rest_framework.decorators import action
from rest_framework.exceptions import PermissionDenied, ValidationError
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from apps.common.search import apply_text_search
from apps.projects.services import projects_visible_to

from .models import Booking, ResourceItem, ResourceType, ResourceUseSubmission
from .serializers import (
    BookingSerializer,
    LaboratoryResourceSerializer,
    ResourceCreateSerializer,
    ResourceItemSerializer,
    ResourceTypeSerializer,
    ResourceUpdateSerializer,
    ResourceUseSubmissionCreateSerializer,
    ResourceUseSubmissionSerializer,
    ResourceUseSubmissionUpdateSerializer,
)
from .services import BookingService, ResourceInventoryService, resource_status_from_contract


class ResourceTypeViewSet(mixins.CreateModelMixin, mixins.ListModelMixin, viewsets.GenericViewSet):
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
        resource_type = serializer.save()
        resource_type.full_clean()


class ResourceItemViewSet(mixins.CreateModelMixin, mixins.ListModelMixin, viewsets.GenericViewSet):
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

    def perform_create(self, serializer):
        resource_item = serializer.save()
        resource_item.full_clean()

    @action(detail=False, methods=["get"], url_path="availability")
    def availability(self, request):
        starts_at = parse_datetime(request.query_params.get("starts_at", ""))
        ends_at = parse_datetime(request.query_params.get("ends_at", ""))
        queryset = self.get_queryset()
        if not starts_at or not ends_at or ends_at <= starts_at:
            raise ValidationError("Availability requires a valid starts_at and ends_at window")
        queryset = queryset.annotate(
            conflicting_booking_count=Count(
                "bookings",
                filter=Q(
                    bookings__status=Booking.Status.RESERVED,
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


class BookingViewSet(
    mixins.CreateModelMixin, mixins.ListModelMixin, mixins.UpdateModelMixin, viewsets.GenericViewSet
):
    serializer_class = BookingSerializer
    permission_classes = [IsAuthenticated]

    def get_project(self):
        return get_object_or_404(
            projects_visible_to(self.request.user), pk=self.kwargs["project_id"]
        )

    def get_queryset(self):
        queryset = Booking.objects.filter(project=self.get_project()).select_related(
            "resource_item", "resource_item__resource_type"
        )
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
            queryset = queryset.filter(status=status_filter)
        resource_item_id = self.request.query_params.get("resource_item_id")
        if resource_item_id:
            queryset = queryset.filter(resource_item_id=resource_item_id)
        return queryset

    def perform_create(self, serializer):
        resource_item = get_object_or_404(
            ResourceItem, pk=serializer.validated_data.pop("resource_item_id")
        )
        try:
            booking = BookingService(self.request.user, self.get_project()).create_booking(
                resource_item=resource_item, **serializer.validated_data
            )
            serializer.instance = booking
        except DjangoValidationError as exc:
            raise ValidationError(exc.messages) from exc

    def perform_update(self, serializer):
        try:
            booking = BookingService(self.request.user, self.get_project()).update_booking(
                serializer.instance, **serializer.validated_data
            )
            serializer.instance = booking
        except DjangoValidationError as exc:
            raise ValidationError(exc.messages) from exc

    @action(detail=True, methods=["post"])
    def cancel(self, request, project_id=None, pk=None):
        booking = get_object_or_404(Booking, project=self.get_project(), pk=pk)
        try:
            booking = BookingService(request.user, self.get_project()).cancel_booking(booking)
        except DjangoValidationError as exc:
            raise ValidationError(exc.messages) from exc
        return Response(BookingSerializer(booking).data)


class LaboratoryResourceViewSet(
    mixins.CreateModelMixin,
    mixins.ListModelMixin,
    mixins.UpdateModelMixin,
    mixins.DestroyModelMixin,
    viewsets.GenericViewSet,
):
    permission_classes = [IsAuthenticated]
    queryset = ResourceItem.objects.select_related("resource_type", "manager").prefetch_related(
        "use_submissions", "use_submissions__student"
    )

    def get_serializer_class(self):
        if self.action == "create":
            return ResourceCreateSerializer
        if self.action in {"partial_update", "update"}:
            return ResourceUpdateSerializer
        if self.action == "use_submissions":
            return ResourceUseSubmissionCreateSerializer
        return LaboratoryResourceSerializer

    def get_queryset(self):
        queryset = self.queryset
        queryset = apply_text_search(
            queryset,
            self.request.query_params.get("search"),
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

    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        try:
            resource = ResourceInventoryService(request.user).create_resource(
                name=serializer.validated_data["name"],
                resource_type=serializer.validated_data["resourceType"],
                description=serializer.validated_data.get("description", ""),
                use_instructions=serializer.validated_data.get("useInstructions", ""),
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
        try:
            resource = ResourceInventoryService(request.user).update_resource(resource, **attrs)
        except PermissionError as exc:
            raise PermissionDenied(str(exc)) from exc
        except DjangoValidationError as exc:
            raise ValidationError(exc.messages) from exc
        return Response(LaboratoryResourceSerializer(resource).data)

    def destroy(self, request, *args, **kwargs):
        try:
            ResourceInventoryService(request.user).retire_resource(self.get_object())
        except PermissionError as exc:
            raise PermissionDenied(str(exc)) from exc
        return Response(status=status.HTTP_204_NO_CONTENT)

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


class ResourceUseSubmissionViewSet(
    mixins.UpdateModelMixin,
    viewsets.GenericViewSet,
):
    serializer_class = ResourceUseSubmissionUpdateSerializer
    permission_classes = [IsAuthenticated]
    queryset = ResourceUseSubmission.objects.select_related("resource_item", "student", "reviewer")

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
