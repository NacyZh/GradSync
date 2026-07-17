from rest_framework import serializers

from .models import (
    InlineComment,
    TeacherFeedback,
    WeeklyProgressReport,
    WritingProject,
    WritingVersion,
)


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
