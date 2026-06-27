from rest_framework import serializers

from .models import Draft, DraftVersion, InlineComment, WeeklyProgressReport


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
