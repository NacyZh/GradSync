from rest_framework import serializers

from .models import PaperAttachment, PaperImportBatch, PaperRecord


class PaperAttachmentSerializer(serializers.ModelSerializer):
    paperId = serializers.CharField(source="paper_id", read_only=True)
    relativePath = serializers.CharField(source="relative_path", read_only=True)
    contentType = serializers.CharField(source="content_type", read_only=True)
    sizeBytes = serializers.IntegerField(source="size_bytes", read_only=True)
    checksumSha256 = serializers.CharField(source="checksum_sha256", read_only=True)

    class Meta:
        model = PaperAttachment
        fields = [
            "id",
            "paperId",
            "filename",
            "relativePath",
            "contentType",
            "sizeBytes",
            "checksumSha256",
            "status",
        ]


class PaperRecordSerializer(serializers.ModelSerializer):
    projectId = serializers.CharField(source="project_id", read_only=True)
    publicationYear = serializers.IntegerField(source="publication_year", required=False)
    externalIds = serializers.JSONField(source="external_ids", required=False)
    importSource = serializers.CharField(source="import_source", read_only=True)
    sourcePathLabel = serializers.CharField(source="source_path_label", read_only=True)
    checksumSha256 = serializers.CharField(source="checksum_sha256", read_only=True)
    uploadedFileId = serializers.CharField(source="uploaded_file_id", read_only=True)
    keywords = serializers.JSONField(source="tags", read_only=True)
    attachments = PaperAttachmentSerializer(many=True, read_only=True)

    class Meta:
        model = PaperRecord
        fields = [
            "id",
            "projectId",
            "title",
            "authors",
            "venue",
            "publicationYear",
            "doi",
            "externalIds",
            "abstract",
            "notes",
            "tags",
            "keywords",
            "visibility",
            "checksumSha256",
            "uploadedFileId",
            "importSource",
            "sourcePathLabel",
            "status",
            "attachments",
        ]


class PaperRecordCreateSerializer(serializers.Serializer):
    title = serializers.CharField(max_length=500)
    authors = serializers.ListField(child=serializers.CharField(), allow_empty=False)
    venue = serializers.CharField(required=False, allow_blank=True)
    publicationYear = serializers.IntegerField(required=False, allow_null=True)
    doi = serializers.CharField(required=False, allow_blank=True)
    externalIds = serializers.JSONField(required=False)
    abstract = serializers.CharField(required=False, allow_blank=True)
    notes = serializers.CharField(required=False, allow_blank=True)
    tags = serializers.ListField(child=serializers.CharField(), required=False)
    sourcePathLabel = serializers.CharField(required=False, allow_blank=True)
    visibility = serializers.ChoiceField(choices=PaperRecord.Visibility.values, required=False)

    def to_internal_value(self, data):
        attrs = super().to_internal_value(data)
        attrs["publication_year"] = attrs.pop("publicationYear", None)
        attrs["external_ids"] = attrs.pop("externalIds", {})
        attrs["source_path_label"] = attrs.pop("sourcePathLabel", "")
        return attrs


def _split_string_list(value) -> list[str]:
    if value is None:
        return []
    if isinstance(value, list):
        return [str(item).strip() for item in value if str(item).strip()]
    return [item.strip() for item in str(value).split(",") if item.strip()]


class PaperUploadSerializer(serializers.Serializer):
    file = serializers.FileField()
    title = serializers.CharField(max_length=500)
    authors = serializers.CharField(required=False, allow_blank=True)
    venue = serializers.CharField(required=False, allow_blank=True)
    publicationYear = serializers.IntegerField(required=False, allow_null=True)
    doi = serializers.CharField(required=False, allow_blank=True)
    abstract = serializers.CharField(required=False, allow_blank=True)
    notes = serializers.CharField(required=False, allow_blank=True)
    tags = serializers.CharField(required=False, allow_blank=True)
    keywords = serializers.CharField(required=False, allow_blank=True)
    visibility = serializers.ChoiceField(
        choices=PaperRecord.Visibility.values,
        required=False,
        default=PaperRecord.Visibility.PROJECT_MEMBERS,
    )

    def to_internal_value(self, data):
        attrs = super().to_internal_value(data)
        attrs["upload"] = attrs.pop("file")
        attrs["authors"] = _split_string_list(attrs.get("authors")) or ["Unknown"]
        keyword_value = attrs.pop("keywords", "") or attrs.pop("tags", "")
        attrs["tags"] = _split_string_list(keyword_value)
        attrs["publication_year"] = attrs.pop("publicationYear", None)
        attrs["external_ids"] = {}
        return attrs


class PaperImportSerializer(serializers.Serializer):
    sourceType = serializers.ChoiceField(choices=PaperImportBatch.SourceType.values)
    sourcePathLabel = serializers.CharField(required=False, allow_blank=True)
    items = PaperRecordCreateSerializer(many=True)

    def to_internal_value(self, data):
        attrs = super().to_internal_value(data)
        attrs["source_type"] = attrs.pop("sourceType")
        attrs["source_path_label"] = attrs.pop("sourcePathLabel", "")
        return attrs


class PaperImportBatchSerializer(serializers.ModelSerializer):
    projectId = serializers.CharField(source="project_id", read_only=True)
    totalItems = serializers.IntegerField(source="total_items", read_only=True)
    acceptedCount = serializers.IntegerField(source="accepted_count", read_only=True)
    duplicateCount = serializers.IntegerField(source="duplicate_count", read_only=True)
    errorCount = serializers.IntegerField(source="error_count", read_only=True)
    results = serializers.JSONField(source="result_summary", read_only=True)
    sourcePathLabel = serializers.CharField(source="source_path_label", read_only=True)

    class Meta:
        model = PaperImportBatch
        fields = [
            "id",
            "projectId",
            "status",
            "sourcePathLabel",
            "totalItems",
            "acceptedCount",
            "duplicateCount",
            "errorCount",
            "results",
        ]
