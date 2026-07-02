from rest_framework import serializers

from .models import PaperAttachment, PaperImportBatch, PaperRecord


class PaperAttachmentSerializer(serializers.ModelSerializer):
    paperId = serializers.CharField(source="paper_id", read_only=True)
    contentType = serializers.CharField(source="content_type", read_only=True)
    sizeBytes = serializers.IntegerField(source="size_bytes", read_only=True)
    checksumSha256 = serializers.CharField(source="checksum_sha256", read_only=True)

    class Meta:
        model = PaperAttachment
        fields = [
            "id",
            "paperId",
            "filename",
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
            "importSource",
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

    def to_internal_value(self, data):
        attrs = super().to_internal_value(data)
        attrs["publication_year"] = attrs.pop("publicationYear", None)
        attrs["external_ids"] = attrs.pop("externalIds", {})
        return attrs


class PaperImportSerializer(serializers.Serializer):
    sourceType = serializers.ChoiceField(choices=PaperImportBatch.SourceType.values)
    items = PaperRecordCreateSerializer(many=True)

    def to_internal_value(self, data):
        attrs = super().to_internal_value(data)
        attrs["source_type"] = attrs.pop("sourceType")
        return attrs


class PaperImportBatchSerializer(serializers.ModelSerializer):
    projectId = serializers.CharField(source="project_id", read_only=True)
    totalItems = serializers.IntegerField(source="total_items", read_only=True)
    acceptedCount = serializers.IntegerField(source="accepted_count", read_only=True)
    duplicateCount = serializers.IntegerField(source="duplicate_count", read_only=True)
    errorCount = serializers.IntegerField(source="error_count", read_only=True)
    results = serializers.JSONField(source="result_summary", read_only=True)

    class Meta:
        model = PaperImportBatch
        fields = [
            "id",
            "projectId",
            "status",
            "totalItems",
            "acceptedCount",
            "duplicateCount",
            "errorCount",
            "results",
        ]
