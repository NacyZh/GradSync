from drf_spectacular.utils import extend_schema_field
from rest_framework import serializers

from .models import (
    DocumentCategory,
    DocumentRecord,
    DuplicateDetectionResult,
    PaperAttachment,
    PaperImportBatch,
    PaperImportJob,
    PaperRecord,
    PaperTitleExtractionResult,
)
from .document_services import document_action_capabilities


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
    canonicalTitle = serializers.CharField(source="canonical_title", read_only=True)
    titleSource = serializers.CharField(source="title_source", read_only=True)
    titleConfidence = serializers.CharField(source="title_confidence", read_only=True)
    downloadAvailable = serializers.SerializerMethodField()
    defaultDownloadFilename = serializers.SerializerMethodField()
    migratedFromLegacyScope = serializers.BooleanField(
        source="migrated_from_legacy_scope", read_only=True
    )
    sharedAccessStartedAt = serializers.DateTimeField(
        source="shared_access_started_at", read_only=True
    )
    createdAt = serializers.DateTimeField(source="created_at", read_only=True)
    publicationYear = serializers.IntegerField(source="publication_year", required=False)
    externalIds = serializers.JSONField(source="external_ids", required=False)
    importSource = serializers.CharField(source="import_source", read_only=True)
    sourcePathLabel = serializers.CharField(source="source_path_label", read_only=True)
    checksumSha256 = serializers.CharField(source="checksum_sha256", read_only=True)
    uploadedFileId = serializers.CharField(source="uploaded_file_id", read_only=True)
    keywords = serializers.JSONField(source="tags", read_only=True)
    attachments = PaperAttachmentSerializer(many=True, read_only=True)
    viewerAvailable = serializers.SerializerMethodField()
    actionCapabilities = serializers.SerializerMethodField()

    class Meta:
        model = PaperRecord
        fields = [
            "id",
            "projectId",
            "title",
            "canonicalTitle",
            "titleSource",
            "titleConfidence",
            "downloadAvailable",
            "defaultDownloadFilename",
            "migratedFromLegacyScope",
            "sharedAccessStartedAt",
            "createdAt",
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
            "viewerAvailable",
            "actionCapabilities",
        ]

    def get_downloadAvailable(self, obj) -> bool:
        return bool(obj.uploaded_file_id or obj.attachments.exists())

    def get_defaultDownloadFilename(self, obj) -> str:
        title = obj.canonical_title or obj.title or "paper"
        safe = "".join(char if char.isalnum() or char in " ._-" else " " for char in title)
        safe = " ".join(safe.split()).strip() or "paper"
        return f"{safe}.pdf"

    def get_viewerAvailable(self, obj) -> bool:
        return obj.status == PaperRecord.Status.ACTIVE

    def get_actionCapabilities(self, obj) -> dict:
        request = self.context.get("request")
        user = getattr(request, "user", None)
        is_maintainer = bool(
            getattr(user, "is_authenticated", False)
            and obj.status == PaperRecord.Status.ACTIVE
            and (getattr(user, "is_administrator", False) or getattr(user, "is_advisor", False))
        )
        can_download = bool(
            obj.status == PaperRecord.Status.ACTIVE
            and (obj.uploaded_file_id or obj.attachments.exists())
        )
        return {
            "canRename": is_maintainer,
            "canDelete": is_maintainer,
            "canDownload": can_download,
            "canView": obj.status == PaperRecord.Status.ACTIVE,
        }


class PaperUploadPolicySerializer(serializers.Serializer):
    category = serializers.CharField()
    maxSizeBytes = serializers.IntegerField(min_value=0)
    displayLabel = serializers.CharField()
    allowedExtensions = serializers.ListField(child=serializers.CharField())
    contentTypes = serializers.ListField(child=serializers.CharField())


class StrictFieldsSerializer(serializers.Serializer):
    def to_internal_value(self, data):
        if hasattr(data, "keys"):
            extra_fields = set(data.keys()) - set(self.fields.keys())
            if extra_fields:
                raise serializers.ValidationError(
                    {field: "Unexpected field." for field in sorted(extra_fields)}
                )
        return super().to_internal_value(data)


class PaperRenameRequestSerializer(StrictFieldsSerializer):
    newTitle = serializers.CharField(max_length=500, trim_whitespace=True)
    reason = serializers.CharField(max_length=255, allow_blank=True, required=False)

    def validate(self, attrs):
        if not attrs["newTitle"].strip():
            raise serializers.ValidationError({"newTitle": "Paper title is required."})
        return attrs


class PaperDeleteRequestSerializer(StrictFieldsSerializer):
    reason = serializers.CharField(max_length=255, allow_blank=True, required=False)


class PaperActionCapabilitiesSerializer(serializers.Serializer):
    canRename = serializers.BooleanField()
    canDelete = serializers.BooleanField()
    canDownload = serializers.BooleanField()
    canView = serializers.BooleanField()


class PaperUnavailableErrorSerializer(serializers.Serializer):
    code = serializers.CharField(default="paper_unavailable")
    message = serializers.CharField()
    paperId = serializers.CharField(required=False)


class PaperTitleExtractionResultSerializer(serializers.ModelSerializer):
    source = serializers.CharField(source="source_attempted", read_only=True)
    extractedTitle = serializers.CharField(source="extracted_title", read_only=True)
    failureReason = serializers.CharField(source="failure_reason", read_only=True)

    class Meta:
        model = PaperTitleExtractionResult
        fields = ["source", "extractedTitle", "confidence", "failureReason"]


class DuplicateDetectionResultSerializer(serializers.ModelSerializer):
    matchBasis = serializers.CharField(source="match_basis", read_only=True)
    candidatePaperId = serializers.CharField(source="candidate_paper_id", read_only=True)
    similarityScore = serializers.FloatField(source="similarity_score", read_only=True)
    reviewStatus = serializers.CharField(source="review_status", read_only=True)

    class Meta:
        model = DuplicateDetectionResult
        fields = ["decision", "matchBasis", "candidatePaperId", "similarityScore", "reviewStatus"]


class PaperImportJobSerializer(serializers.ModelSerializer):
    requestedBy = serializers.CharField(source="requested_by_id", read_only=True)
    userMessage = serializers.CharField(source="user_message", read_only=True)
    acceptedPaper = PaperRecordSerializer(source="accepted_paper", read_only=True)
    duplicatePaper = PaperRecordSerializer(source="duplicate_paper", read_only=True)
    extraction = serializers.SerializerMethodField()
    duplicateDetection = serializers.SerializerMethodField()
    failureReason = serializers.CharField(source="failure_reason", read_only=True)
    createdAt = serializers.DateTimeField(source="created_at", read_only=True)
    updatedAt = serializers.DateTimeField(source="updated_at", read_only=True)
    completedAt = serializers.DateTimeField(source="completed_at", read_only=True)

    class Meta:
        model = PaperImportJob
        fields = [
            "id",
            "status",
            "requestedBy",
            "userMessage",
            "acceptedPaper",
            "duplicatePaper",
            "extraction",
            "duplicateDetection",
            "failureReason",
            "createdAt",
            "updatedAt",
            "completedAt",
        ]

    @extend_schema_field(PaperTitleExtractionResultSerializer(allow_null=True))
    def get_extraction(self, obj):
        if not obj.paper_file_id:
            return None
        result = obj.paper_file.title_extraction_results.first()
        if result is None:
            return None
        return PaperTitleExtractionResultSerializer(result).data

    @extend_schema_field(DuplicateDetectionResultSerializer(allow_null=True))
    def get_duplicateDetection(self, obj):
        if not obj.paper_file_id:
            return None
        result = obj.paper_file.duplicate_detection_results.first()
        if result is None:
            return None
        return DuplicateDetectionResultSerializer(result).data


class UploadErrorSerializer(serializers.Serializer):
    code = serializers.CharField()
    message = serializers.CharField()
    reason = serializers.CharField()


class PaperPdfImportSerializer(serializers.Serializer):
    file = serializers.FileField()

    def validate(self, attrs):
        extra_fields = set(self.initial_data) - {"file"}
        if extra_fields:
            raise serializers.ValidationError("Paper import accepts only a PDF file.")
        return attrs


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


class DocumentCategorySerializer(serializers.ModelSerializer):
    createdById = serializers.CharField(source="created_by_id", read_only=True)

    class Meta:
        model = DocumentCategory
        fields = ["id", "name", "description", "status", "createdById"]


class DocumentCategoryCreateSerializer(serializers.Serializer):
    name = serializers.CharField(max_length=120)
    description = serializers.CharField(required=False, allow_blank=True)


class DocumentRecordSerializer(serializers.ModelSerializer):
    projectId = serializers.CharField(source="project_id", read_only=True)
    categoryId = serializers.CharField(source="category_id", read_only=True)
    categoryName = serializers.CharField(source="category.name", read_only=True)
    uploaderId = serializers.CharField(source="created_by_id", read_only=True)
    documentFileId = serializers.CharField(source="document_file_id", read_only=True)
    checksumSha256 = serializers.CharField(source="checksum_sha256", read_only=True)
    createdAt = serializers.DateTimeField(source="created_at", read_only=True)
    actionCapabilities = serializers.SerializerMethodField()

    class Meta:
        model = DocumentRecord
        fields = [
            "id",
            "projectId",
            "visibility",
            "uploaderId",
            "createdAt",
            "categoryId",
            "categoryName",
            "title",
            "description",
            "documentFileId",
            "checksumSha256",
            "status",
            "actionCapabilities",
        ]

    @extend_schema_field(
        {
            "type": "object",
            "properties": {
                "canView": {"type": "boolean"},
                "canDownload": {"type": "boolean"},
                "canRename": {"type": "boolean"},
                "canDelete": {"type": "boolean"},
                "canUploadGroupWide": {"type": "boolean"},
            },
            "required": [
                "canView",
                "canDownload",
                "canRename",
                "canDelete",
                "canUploadGroupWide",
            ],
        }
    )
    def get_actionCapabilities(self, obj):
        request = self.context.get("request")
        return document_action_capabilities(getattr(request, "user", None), obj)


class DocumentUploadSerializer(serializers.Serializer):
    file = serializers.FileField()
    title = serializers.CharField(max_length=255, required=False, allow_blank=True)
    categoryId = serializers.IntegerField()
    description = serializers.CharField(required=False, allow_blank=True)
    visibility = serializers.ChoiceField(
        choices=DocumentRecord.Visibility.values,
        required=False,
        default=DocumentRecord.Visibility.PROJECT_MEMBERS,
    )

    def to_internal_value(self, data):
        attrs = super().to_internal_value(data)
        attrs["upload"] = attrs.pop("file")
        attrs["category_id"] = attrs.pop("categoryId")
        return attrs


class DocumentRenameRequestSerializer(StrictFieldsSerializer):
    newTitle = serializers.CharField(max_length=255, trim_whitespace=True)
    reason = serializers.CharField(max_length=255, allow_blank=True, required=False)

    def validate(self, attrs):
        if not attrs["newTitle"].strip():
            raise serializers.ValidationError({"newTitle": "Document title is required."})
        return attrs


class DocumentDeleteRequestSerializer(StrictFieldsSerializer):
    reason = serializers.CharField(max_length=255, allow_blank=True, required=False)
