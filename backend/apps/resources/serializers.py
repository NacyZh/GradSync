from drf_spectacular.utils import extend_schema_field
from rest_framework import serializers

from .models import Booking, ResourceItem, ResourceType, ResourceUseSubmission
from .services import current_use_periods_by_resource, resource_status_to_contract


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
    confirmationPolicy = serializers.ChoiceField(
        source="confirmation_policy", choices=ResourceType.ConfirmationPolicy.choices
    )

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
            "confirmationPolicy",
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
    resourceType = serializers.CharField(source="resource_type.name", read_only=True)
    totalQuantity = serializers.IntegerField(source="total_quantity")
    availableQuantity = serializers.IntegerField(read_only=True, required=False)
    allocatedQuantity = serializers.IntegerField(read_only=True, required=False)
    currentUsePeriods = serializers.SerializerMethodField()
    confirmationPolicyOverride = serializers.ChoiceField(
        source="confirmation_policy_override",
        choices=ResourceType.ConfirmationPolicy.choices,
        allow_null=True,
        required=False,
    )
    effectiveConfirmationPolicy = serializers.CharField(
        source="effective_confirmation_policy", read_only=True
    )

    class Meta:
        model = ResourceItem
        fields = [
            "id",
            "resourceTypeId",
            "resourceType",
            "name",
            "description",
            "location",
            "totalQuantity",
            "availableQuantity",
            "allocatedQuantity",
            "currentUsePeriods",
            "fieldValues",
            "availabilityPolicy",
            "status",
            "confirmationPolicyOverride",
            "effectiveConfirmationPolicy",
            "version",
            "available",
            "conflictingBookingCount",
        ]

    @extend_schema_field(serializers.ListField(child=serializers.DictField()))
    def get_currentUsePeriods(self, obj):
        periods = getattr(obj, "current_use_periods", None)
        if periods is not None:
            return periods
        return current_use_periods_by_resource([obj.pk]).get(obj.pk, [])


class BookingSerializer(serializers.ModelSerializer):
    resourceId = serializers.IntegerField(source="resource_item_id")
    resourceName = serializers.CharField(source="resource_item.name", read_only=True)
    requestedById = serializers.IntegerField(source="requested_by_id", read_only=True)
    requesterName = serializers.CharField(source="requested_by.name", read_only=True)
    reviewerId = serializers.IntegerField(source="reviewer_id", read_only=True)
    startsAt = serializers.DateTimeField(source="starts_at")
    endsAt = serializers.DateTimeField(source="ends_at")
    confirmationPolicy = serializers.CharField(source="confirmation_policy", read_only=True)
    decisionNote = serializers.CharField(source="decision_note", read_only=True)
    completedAt = serializers.DateTimeField(source="completed_at", read_only=True)
    cancelledAt = serializers.DateTimeField(source="cancelled_at", read_only=True)
    createdAt = serializers.DateTimeField(source="created_at", read_only=True)

    class Meta:
        model = Booking
        fields = [
            "id",
            "resourceId",
            "resourceName",
            "requestedById",
            "requesterName",
            "startsAt",
            "endsAt",
            "quantity",
            "origin",
            "confirmationPolicy",
            "status",
            "purpose",
            "reviewerId",
            "decisionNote",
            "completedAt",
            "cancelledAt",
            "createdAt",
            "version",
        ]
        read_only_fields = ["status", "version", "origin"]


class BookingDecisionSerializer(serializers.Serializer):
    decisionNote = serializers.CharField(required=False, allow_blank=True)


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
    resourceTypeId = serializers.IntegerField(source="resource_type_id", read_only=True)
    totalQuantity = serializers.IntegerField(source="total_quantity", read_only=True)
    availableQuantity = serializers.SerializerMethodField()
    currentUsePeriods = serializers.SerializerMethodField()
    confirmationPolicyOverride = serializers.CharField(
        source="confirmation_policy_override", read_only=True, allow_null=True
    )
    effectiveConfirmationPolicy = serializers.CharField(
        source="effective_confirmation_policy", read_only=True
    )
    status = serializers.SerializerMethodField()

    class Meta:
        model = ResourceItem
        fields = [
            "id",
            "name",
            "resourceType",
            "resourceTypeId",
            "description",
            "location",
            "totalQuantity",
            "availableQuantity",
            "currentUsePeriods",
            "status",
            "managerId",
            "useInstructions",
            "confirmationPolicyOverride",
            "effectiveConfirmationPolicy",
            "version",
        ]

    @extend_schema_field(serializers.CharField())
    def get_status(self, obj):
        return resource_status_to_contract(obj.status)

    @extend_schema_field(serializers.IntegerField())
    def get_availableQuantity(self, obj):
        return getattr(obj, "available_quantity", obj.total_quantity)

    @extend_schema_field(serializers.ListField(child=serializers.DictField()))
    def get_currentUsePeriods(self, obj):
        periods = getattr(obj, "current_use_periods", None)
        if periods is not None:
            return periods
        return current_use_periods_by_resource([obj.pk]).get(obj.pk, [])


class ResourceCreateSerializer(serializers.Serializer):
    name = serializers.CharField()
    resourceType = serializers.CharField()
    totalQuantity = serializers.IntegerField(min_value=1)
    location = serializers.CharField(required=False, allow_blank=True)
    description = serializers.CharField(required=False, allow_blank=True)
    status = serializers.ChoiceField(
        choices=["active", ResourceItem.Status.UNAVAILABLE], default="active"
    )
    useInstructions = serializers.CharField(required=False, allow_blank=True)
    confirmationPolicyOverride = serializers.ChoiceField(
        choices=ResourceType.ConfirmationPolicy.choices, required=False, allow_null=True
    )


class ResourceUpdateSerializer(serializers.Serializer):
    version = serializers.IntegerField(min_value=1)
    name = serializers.CharField(required=False)
    resourceType = serializers.CharField(required=False)
    description = serializers.CharField(required=False, allow_blank=True)
    location = serializers.CharField(required=False, allow_blank=True)
    totalQuantity = serializers.IntegerField(min_value=1, required=False)
    status = serializers.ChoiceField(
        choices=["active", ResourceItem.Status.UNAVAILABLE, ResourceItem.Status.RETIRED],
        required=False,
    )
    useInstructions = serializers.CharField(required=False, allow_blank=True)
    confirmationPolicyOverride = serializers.ChoiceField(
        choices=ResourceType.ConfirmationPolicy.choices, required=False, allow_null=True
    )


class ResourceUseSubmissionCreateSerializer(serializers.Serializer):
    submissionType = serializers.ChoiceField(choices=ResourceUseSubmission.SubmissionType.values)
    details = serializers.CharField()


class ResourceUseSubmissionUpdateSerializer(serializers.Serializer):
    status = serializers.ChoiceField(
        choices=[ResourceUseSubmission.Status.CONFIRMED, ResourceUseSubmission.Status.REJECTED]
    )
    decisionNote = serializers.CharField(required=False, allow_blank=True)
