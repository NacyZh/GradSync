from rest_framework import serializers

from .models import (
    Draft,
    DraftVersion,
    InlineComment,
    TeacherFeedback,
    WeeklyProgressReport,
    WritingProject,
    WritingVersion,
)


class DraftSerializer(serializers.ModelSerializer):
    class Meta:
        model = Draft
        fields = ["id", "project_id", "title", "student_id", "status"]
        read_only_fields = ["project_id", "student_id", "status"]


class DraftVersionSerializer(serializers.ModelSerializer):
    class Meta:
        model = DraftVersion
        fields = [
            "id",
            "draft_id",
            "project_id",
            "version_number",
            "submitted_by_id",
            "content_reference",
            "summary",
            "review_status",
            "submitted_at",
        ]
        read_only_fields = [
            "draft_id",
            "project_id",
            "version_number",
            "submitted_by_id",
            "review_status",
            "submitted_at",
        ]


class ReviewStatusSerializer(serializers.Serializer):
    review_status = serializers.ChoiceField(choices=DraftVersion.ReviewStatus.choices)


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
            "review_status",
        ]
        read_only_fields = ["project_id", "student_id", "review_status"]


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
    studentId = serializers.CharField(source="student_id", read_only=True)
    writingType = serializers.CharField(source="writing_type")
    versions = WritingVersionSerializer(many=True, read_only=True)

    class Meta:
        model = WritingProject
        fields = [
            "id",
            "projectId",
            "studentId",
            "title",
            "writingType",
            "status",
            "versions",
        ]
        read_only_fields = ["projectId", "studentId", "status", "versions"]

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
