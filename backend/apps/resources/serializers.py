from drf_spectacular.utils import extend_schema_field
from rest_framework import serializers

from .models import Booking, ResourceItem, ResourceType, ResourceUseSubmission
from .services import resource_status_to_contract


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


class ResourceUseSubmissionSerializer(serializers.ModelSerializer):
    resourceId = serializers.IntegerField(source="resource_item_id", read_only=True)
    studentId = serializers.IntegerField(source="student_id", read_only=True)
    studentName = serializers.CharField(source="student.name", read_only=True)
    submissionType = serializers.CharField(source="submission_type", read_only=True)
    decisionNote = serializers.CharField(source="decision_note", read_only=True)
    reviewerId = serializers.IntegerField(source="reviewer_id", read_only=True)

    class Meta:
        model = ResourceUseSubmission
        fields = [
            "id",
            "resourceId",
            "studentId",
            "studentName",
            "submissionType",
            "details",
            "status",
            "reviewerId",
            "decisionNote",
            "submitted_at",
            "decided_at",
        ]


class LaboratoryResourceSerializer(serializers.ModelSerializer):
    resourceType = serializers.CharField(source="resource_type.name", read_only=True)
    useInstructions = serializers.CharField(source="use_instructions", read_only=True)
    managerId = serializers.IntegerField(source="manager_id", read_only=True)
    useSubmissions = ResourceUseSubmissionSerializer(
        source="use_submissions", many=True, read_only=True
    )
    status = serializers.SerializerMethodField()

    class Meta:
        model = ResourceItem
        fields = [
            "id",
            "name",
            "resourceType",
            "description",
            "status",
            "managerId",
            "useInstructions",
            "useSubmissions",
        ]

    @extend_schema_field(serializers.CharField())
    def get_status(self, obj):
        return resource_status_to_contract(obj.status)


class ResourceCreateSerializer(serializers.Serializer):
    name = serializers.CharField()
    resourceType = serializers.CharField()
    description = serializers.CharField(required=False, allow_blank=True)
    useInstructions = serializers.CharField(required=False, allow_blank=True)


class ResourceUpdateSerializer(serializers.Serializer):
    name = serializers.CharField(required=False)
    resourceType = serializers.CharField(required=False)
    description = serializers.CharField(required=False, allow_blank=True)
    status = serializers.ChoiceField(
        choices=["active", ResourceItem.Status.UNAVAILABLE, ResourceItem.Status.RETIRED],
        required=False,
    )
    useInstructions = serializers.CharField(required=False, allow_blank=True)


class ResourceUseSubmissionCreateSerializer(serializers.Serializer):
    submissionType = serializers.ChoiceField(choices=ResourceUseSubmission.SubmissionType.values)
    details = serializers.CharField()


class ResourceUseSubmissionUpdateSerializer(serializers.Serializer):
    status = serializers.ChoiceField(
        choices=[ResourceUseSubmission.Status.CONFIRMED, ResourceUseSubmission.Status.REJECTED]
    )
    decisionNote = serializers.CharField(required=False, allow_blank=True)
