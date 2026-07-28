from rest_framework import serializers

from .models import (
    InlineComment,
    ProjectReportSchedule,
    ReportingPeriod,
    ReportResponse,
    ReportTemplateField,
    ReportTemplateVersion,
    SubmissionReviewAssignment,
    TeacherFeedback,
    WeeklyProgressReport,
    WritingProject,
    WritingVersion,
)


class ReportTemplateFieldSerializer(serializers.ModelSerializer):
    labelEn = serializers.CharField(source="label_en")
    labelZh = serializers.CharField(source="label_zh")
    helpTextEn = serializers.CharField(source="help_text_en", required=False)
    helpTextZh = serializers.CharField(source="help_text_zh", required=False)
    fieldType = serializers.CharField(source="field_type")
    minValue = serializers.DecimalField(
        source="min_value", max_digits=14, decimal_places=4, allow_null=True
    )
    maxValue = serializers.DecimalField(
        source="max_value", max_digits=14, decimal_places=4, allow_null=True
    )
    analyticsEnabled = serializers.BooleanField(source="analytics_enabled")

    class Meta:
        model = ReportTemplateField
        fields = [
            "id",
            "key",
            "labelEn",
            "labelZh",
            "helpTextEn",
            "helpTextZh",
            "fieldType",
            "required",
            "order",
            "unit",
            "options",
            "minValue",
            "maxValue",
            "analyticsEnabled",
        ]


class ReportTemplateVersionSerializer(serializers.ModelSerializer):
    templateId = serializers.IntegerField(source="template_id", read_only=True)
    projectId = serializers.IntegerField(source="project_id", read_only=True)
    name = serializers.CharField(source="template.name", read_only=True)
    versionNumber = serializers.IntegerField(source="version_number", read_only=True)
    publishedAt = serializers.DateTimeField(source="published_at", read_only=True, allow_null=True)
    fields = ReportTemplateFieldSerializer(many=True, read_only=True)

    class Meta:
        model = ReportTemplateVersion
        fields = [
            "id",
            "templateId",
            "projectId",
            "name",
            "versionNumber",
            "status",
            "version",
            "fields",
            "publishedAt",
        ]


class ReportingPeriodSerializer(serializers.ModelSerializer):
    projectId = serializers.IntegerField(source="project_id", read_only=True)
    startsOn = serializers.DateField(source="starts_on")
    endsOn = serializers.DateField(source="ends_on")
    deadlineAt = serializers.DateTimeField(source="deadline_at")
    templateVersionId = serializers.IntegerField(source="template_version_id", read_only=True)
    currentUserReportStatus = serializers.SerializerMethodField()

    class Meta:
        model = ReportingPeriod
        fields = [
            "id",
            "projectId",
            "startsOn",
            "endsOn",
            "deadlineAt",
            "templateVersionId",
            "state",
            "currentUserReportStatus",
        ]

    def get_currentUserReportStatus(self, obj):
        user = self.context.get("user")
        if not user:
            return None
        report = obj.reports.filter(student=user).order_by("-revision_number").first()
        return report.review_status if report else "missing"


class StructuredReportResponseSerializer(serializers.ModelSerializer):
    fieldId = serializers.IntegerField(source="template_field_id")
    sourceType = serializers.CharField(source="source_type")
    sourceId = serializers.CharField(source="source_id")

    class Meta:
        model = ReportResponse
        fields = ["fieldId", "value", "sourceType", "sourceId"]


class StructuredReportSerializer(serializers.ModelSerializer):
    projectId = serializers.IntegerField(source="project_id", read_only=True)
    student = serializers.SerializerMethodField()
    reportingPeriod = ReportingPeriodSerializer(source="reporting_period")
    templateVersionId = serializers.IntegerField(source="template_version_id", read_only=True)
    revisionNumber = serializers.IntegerField(source="revision_number")
    reviewStatus = serializers.CharField(source="review_status")
    submittedAt = serializers.DateTimeField(source="submitted_at")
    submittedLate = serializers.BooleanField(source="submitted_late")
    responses = StructuredReportResponseSerializer(many=True)

    class Meta:
        model = WeeklyProgressReport
        fields = [
            "id",
            "projectId",
            "student",
            "reportingPeriod",
            "templateVersionId",
            "revisionNumber",
            "reviewStatus",
            "submittedAt",
            "submittedLate",
            "responses",
        ]

    def get_student(self, obj):
        return {
            "id": obj.student_id,
            "displayName": obj.student.name,
            "role": obj.student.global_role,
        }


class ReportSubmissionSerializer(serializers.Serializer):
    reportingPeriodId = serializers.IntegerField()
    responses = serializers.ListField(child=serializers.DictField(), min_length=1)
    attachmentReference = serializers.CharField(required=False, allow_blank=True, max_length=512)
    idempotencyKey = serializers.CharField(min_length=8, max_length=100)


class SubmissionReviewAssignmentSerializer(serializers.ModelSerializer):
    reviewerMembershipId = serializers.IntegerField(source="reviewer_membership_id", required=False)
    weeklyReportId = serializers.IntegerField(
        source="weekly_report_id", required=False, allow_null=True
    )
    writingVersionId = serializers.IntegerField(
        source="writing_version_id", required=False, allow_null=True
    )
    draftVersionId = serializers.IntegerField(
        source="draft_version_id", required=False, allow_null=True
    )
    deliverableRevisionId = serializers.IntegerField(
        source="deliverable_revision_id", required=False, allow_null=True
    )
    reviewerName = serializers.CharField(source="reviewer_membership.user.name", read_only=True)

    class Meta:
        model = SubmissionReviewAssignment
        fields = [
            "id",
            "reviewerMembershipId",
            "reviewerName",
            "weeklyReportId",
            "writingVersionId",
            "draftVersionId",
            "deliverableRevisionId",
            "status",
            "version",
            "assigned_at",
            "removed_at",
        ]
        read_only_fields = [
            "id",
            "reviewerName",
            "status",
            "version",
            "assigned_at",
            "removed_at",
        ]


class ProjectReportScheduleWriteSerializer(serializers.Serializer):
    weekday = serializers.IntegerField(min_value=1, max_value=7)
    deadlineLocalTime = serializers.TimeField()
    timezone = serializers.CharField(max_length=64)
    expectedVersion = serializers.IntegerField(min_value=0, required=False, allow_null=True)


class ProjectReportScheduleDeleteSerializer(serializers.Serializer):
    expectedVersion = serializers.IntegerField(min_value=1)


class ProjectReportScheduleSerializer(serializers.ModelSerializer):
    projectId = serializers.IntegerField(source="project_id", read_only=True)
    deadlineLocalTime = serializers.TimeField(source="deadline_time", format="%H:%M")
    updatedBy = serializers.SerializerMethodField()
    createdAt = serializers.DateTimeField(source="created_at", read_only=True)
    updatedAt = serializers.DateTimeField(source="updated_at", read_only=True)

    class Meta:
        model = ProjectReportSchedule
        fields = [
            "id",
            "projectId",
            "weekday",
            "deadlineLocalTime",
            "timezone",
            "version",
            "updatedBy",
            "createdAt",
            "updatedAt",
        ]

    def get_updatedBy(self, obj):
        return {
            "id": obj.updated_by_id,
            "name": obj.updated_by.name,
            "role": obj.updated_by.global_role,
        }


class ReviewStatusSerializer(serializers.Serializer):
    review_status = serializers.ChoiceField(choices=WeeklyProgressReport.ReviewStatus.choices)


class WeeklyReportSerializer(serializers.ModelSerializer):
    class Meta:
        model = WeeklyProgressReport
        fields = [
            "id",
            "project_id",
            "student_id",
            "report_week_start",
            "completed_work",
            "blockers",
            "next_steps",
            "attachment_reference",
            "revision_number",
            "review_status",
            "submitted_at",
            "reviewed_at",
        ]
        read_only_fields = [
            "project_id",
            "student_id",
            "revision_number",
            "review_status",
            "submitted_at",
            "reviewed_at",
        ]


class InlineCommentSerializer(serializers.ModelSerializer):
    class Meta:
        model = InlineComment
        fields = [
            "id",
            "project_id",
            "target_type",
            "target_id",
            "author_id",
            "anchor",
            "body",
            "status",
        ]
        read_only_fields = ["project_id", "author_id", "status"]


class InlineCommentStatusSerializer(serializers.Serializer):
    status = serializers.ChoiceField(choices=InlineComment.Status.choices)


class TeacherFeedbackSerializer(serializers.ModelSerializer):
    writingVersionId = serializers.CharField(source="writing_version_id", read_only=True)
    reviewerId = serializers.CharField(source="reviewer_id", read_only=True)
    annotatedFileId = serializers.CharField(source="annotated_file_id", read_only=True)
    annotatedFileName = serializers.CharField(
        source="annotated_file.original_filename", read_only=True
    )
    notificationStatus = serializers.CharField(source="notification.status", read_only=True)

    class Meta:
        model = TeacherFeedback
        fields = [
            "id",
            "writingVersionId",
            "reviewerId",
            "comments",
            "status",
            "annotatedFileId",
            "annotatedFileName",
            "notificationStatus",
            "submitted_at",
        ]


class WritingVersionSerializer(serializers.ModelSerializer):
    writingProjectId = serializers.CharField(source="writing_project_id", read_only=True)
    versionNumber = serializers.IntegerField(source="version_number", read_only=True)
    submittedById = serializers.CharField(source="submitted_by_id", read_only=True)
    draftFileId = serializers.CharField(source="draft_file_id", read_only=True)
    draftFileName = serializers.CharField(source="draft_file.original_filename", read_only=True)
    fileKind = serializers.CharField(source="file_kind", read_only=True)
    submittedAt = serializers.DateTimeField(source="submitted_at", read_only=True)
    feedback = TeacherFeedbackSerializer(many=True, read_only=True)

    class Meta:
        model = WritingVersion
        fields = [
            "id",
            "writingProjectId",
            "versionNumber",
            "submittedById",
            "draftFileId",
            "draftFileName",
            "fileKind",
            "summary",
            "status",
            "submittedAt",
            "feedback",
        ]


class WritingProjectSerializer(serializers.ModelSerializer):
    projectId = serializers.CharField(source="project_id", read_only=True)
    legacyProjectId = serializers.CharField(source="legacy_project_id", read_only=True)
    studentId = serializers.CharField(source="student_id", read_only=True)
    writingType = serializers.CharField(source="writing_type")
    participantRole = serializers.SerializerMethodField()
    versions = WritingVersionSerializer(many=True, read_only=True)

    class Meta:
        model = WritingProject
        fields = [
            "id",
            "projectId",
            "legacyProjectId",
            "studentId",
            "title",
            "writingType",
            "participantRole",
            "status",
            "versions",
        ]
        read_only_fields = [
            "projectId",
            "legacyProjectId",
            "studentId",
            "participantRole",
            "status",
            "versions",
        ]

    def get_participantRole(self, obj):
        from .writing_participant_services import participant_role_for

        request = self.context.get("request")
        return participant_role_for(getattr(request, "user", None), obj) if request else ""

    def to_internal_value(self, data):
        attrs = super().to_internal_value(data)
        attrs["writing_type"] = attrs.pop("writing_type", attrs.get("writingType", ""))
        return attrs


class WritingProjectCreateSerializer(serializers.Serializer):
    title = serializers.CharField(max_length=255)
    writingType = serializers.ChoiceField(choices=WritingProject.WritingType.values)

    def to_internal_value(self, data):
        attrs = super().to_internal_value(data)
        attrs["writing_type"] = attrs.pop("writingType")
        return attrs


class WritingProjectRenameSerializer(serializers.Serializer):
    title = serializers.CharField(max_length=255)


class WritingVersionUploadSerializer(serializers.Serializer):
    file = serializers.FileField()
    summary = serializers.CharField(required=False, allow_blank=True)

    def to_internal_value(self, data):
        attrs = super().to_internal_value(data)
        attrs["upload"] = attrs.pop("file")
        return attrs


class TeacherFeedbackCreateSerializer(serializers.Serializer):
    annotatedFile = serializers.FileField()
    comments = serializers.CharField(required=False, allow_blank=True)

    def to_internal_value(self, data):
        attrs = super().to_internal_value(data)
        attrs["annotated_file"] = attrs.pop("annotatedFile")
        return attrs
