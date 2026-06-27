from django.core.exceptions import ValidationError as DjangoValidationError
from django.db.models import Count, Q
from django.shortcuts import get_object_or_404
from django.utils.dateparse import parse_datetime
from rest_framework import mixins, viewsets
from rest_framework.decorators import action
from rest_framework.exceptions import ValidationError
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from apps.common.search import apply_text_search
from apps.projects.services import projects_visible_to

from .models import Booking, LabResource
from .serializers import BookingSerializer, LabResourceSerializer
from .services import BookingService


class LabResourceViewSet(mixins.ListModelMixin, viewsets.GenericViewSet):
    serializer_class = LabResourceSerializer
    permission_classes = [IsAuthenticated]
    queryset = LabResource.objects.all()

    def get_queryset(self):
        queryset = LabResource.objects.all()
        queryset = apply_text_search(
            queryset, self.request.query_params.get("search"), ["name", "location"]
        )
        status_filter = self.request.query_params.get("status")
        if status_filter:
            queryset = queryset.filter(status=status_filter)
        return queryset

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
                resource.status == LabResource.Status.AVAILABLE
                and resource.conflicting_booking_count == 0
            )
        return Response(LabResourceSerializer(resources, many=True).data)


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
        queryset = Booking.objects.filter(project=self.get_project()).select_related("resource")
        queryset = apply_text_search(
            queryset,
            self.request.query_params.get("search"),
            ["purpose", "resource__name", "resource__location"],
        )
        status_filter = self.request.query_params.get("status")
        if status_filter:
            queryset = queryset.filter(status=status_filter)
        resource_id = self.request.query_params.get("resource_id")
        if resource_id:
            queryset = queryset.filter(resource_id=resource_id)
        return queryset

    def perform_create(self, serializer):
        resource = get_object_or_404(LabResource, pk=serializer.validated_data.pop("resource_id"))
        try:
            booking = BookingService(self.request.user, self.get_project()).create_booking(
                resource=resource, **serializer.validated_data
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
