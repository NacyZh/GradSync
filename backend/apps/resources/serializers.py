from rest_framework import serializers

from .models import Booking, LabResource


class LabResourceSerializer(serializers.ModelSerializer):
    available = serializers.BooleanField(read_only=True, required=False)
    conflicting_booking_count = serializers.IntegerField(read_only=True, required=False)

    class Meta:
        model = LabResource
        fields = [
            "id",
            "name",
            "resource_type",
            "location",
            "status",
            "available",
            "conflicting_booking_count",
        ]


class BookingSerializer(serializers.ModelSerializer):
    resource_id = serializers.IntegerField()

    class Meta:
        model = Booking
        fields = [
            "id",
            "project_id",
            "resource_id",
            "requested_by_id",
            "starts_at",
            "ends_at",
            "status",
            "purpose",
        ]
        read_only_fields = ["project_id", "requested_by_id", "status"]
