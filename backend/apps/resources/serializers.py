from rest_framework import serializers

from .models import Booking, ResourceItem, ResourceType


class ResourceFieldSerializer(serializers.Serializer):
    key = serializers.CharField()
    label = serializers.CharField()
    fieldType = serializers.ChoiceField(choices=sorted(ResourceType.SUPPORTED_FIELD_TYPES))
    required = serializers.BooleanField(default=False)
    options = serializers.ListField(child=serializers.CharField(), required=False)

    def to_internal_value(self, data):
        attrs = super().to_internal_value(data)
        attrs["field_type"] = attrs.pop("fieldType")
        return attrs

    def to_representation(self, instance):
        data = dict(instance)
        data["fieldType"] = data.pop("field_type", data.get("fieldType"))
        return data


class ResourceTypeSerializer(serializers.ModelSerializer):
    fieldSchema = serializers.JSONField(source="field_schema")
    eligibilityPolicy = serializers.JSONField(source="eligibility_policy", required=False)
    bookingPolicy = serializers.JSONField(source="booking_policy", required=False)

    class Meta:
        model = ResourceType
        fields = [
            "id",
            "name",
            "description",
            "scope",
            "fieldSchema",
            "eligibilityPolicy",
            "bookingPolicy",
            "status",
        ]


class ResourceItemSerializer(serializers.ModelSerializer):
    resourceTypeId = serializers.IntegerField(source="resource_type_id")
    fieldValues = serializers.JSONField(source="field_values", required=False)
    availabilityPolicy = serializers.JSONField(source="availability_policy", required=False)
    available = serializers.BooleanField(read_only=True, required=False)
    conflictingBookingCount = serializers.IntegerField(
        source="conflicting_booking_count", read_only=True, required=False
    )

    class Meta:
        model = ResourceItem
        fields = [
            "id",
            "resourceTypeId",
            "name",
            "description",
            "location",
            "fieldValues",
            "availabilityPolicy",
            "status",
            "available",
            "conflictingBookingCount",
        ]


class BookingSerializer(serializers.ModelSerializer):
    resourceItemId = serializers.IntegerField(source="resource_item_id")

    class Meta:
        model = Booking
        fields = [
            "id",
            "project_id",
            "resourceItemId",
            "requested_by_id",
            "starts_at",
            "ends_at",
            "status",
            "purpose",
        ]
        read_only_fields = ["project_id", "requested_by_id", "status"]
