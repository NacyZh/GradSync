from drf_spectacular.utils import extend_schema_field
from rest_framework import serializers

from apps.projects.material_services import classify_workspace_record, source_project_payload

from .models import CodeArtifact, CodeArtifactVersion
from .services import can_manage_code_artifact, can_manage_shared_code_artifact


class CodeArtifactVersionSerializer(serializers.ModelSerializer):
    artifactId = serializers.CharField(source="artifact_id", read_only=True)
    projectId = serializers.CharField(source="project_id", read_only=True)
    versionLabel = serializers.CharField(source="version_label", read_only=True)
    commitReference = serializers.CharField(source="commit_reference", read_only=True)
    releaseNotes = serializers.CharField(source="release_notes", read_only=True)
    relativePathManifest = serializers.JSONField(source="relative_path_manifest", read_only=True)
    contentType = serializers.CharField(source="content_type", read_only=True)
    sizeBytes = serializers.IntegerField(source="size_bytes", read_only=True)
    checksumSha256 = serializers.CharField(source="checksum_sha256", read_only=True)

    class Meta:
        model = CodeArtifactVersion
        fields = [
            "id",
            "artifactId",
            "projectId",
            "versionLabel",
            "commitReference",
            "releaseNotes",
            "description",
            "filename",
            "relativePathManifest",
            "contentType",
            "sizeBytes",
            "checksumSha256",
            "status",
        ]


class CodeArtifactSerializer(serializers.ModelSerializer):
    projectId = serializers.CharField(source="project_id", read_only=True)
    sourcePathLabel = serializers.CharField(source="source_path_label", read_only=True)
    checksumSha256 = serializers.CharField(source="checksum_sha256", read_only=True)
    archiveFileId = serializers.CharField(source="archive_file_id", read_only=True)
    latestVersion = serializers.SerializerMethodField()
    actionCapabilities = serializers.SerializerMethodField()
    boundaryType = serializers.SerializerMethodField()
    sourceProject = serializers.SerializerMethodField()

    class Meta:
        model = CodeArtifact
        fields = [
            "id",
            "projectId",
            "name",
            "description",
            "tags",
            "sourcePathLabel",
            "visibility",
            "boundaryType",
            "sourceProject",
            "checksumSha256",
            "archiveFileId",
            "status",
            "latestVersion",
            "actionCapabilities",
        ]

    @extend_schema_field(CodeArtifactVersionSerializer(allow_null=True))
    def get_latestVersion(self, obj):
        version = obj.versions.filter(status=CodeArtifactVersion.Status.ACTIVE).first()
        return CodeArtifactVersionSerializer(version).data if version else None

    @extend_schema_field(
        {
            "type": "object",
            "properties": {
                "canView": {"type": "boolean"},
                "canDownload": {"type": "boolean"},
                "canRename": {"type": "boolean"},
                "canDelete": {"type": "boolean"},
            },
            "required": ["canView", "canDownload", "canRename", "canDelete"],
        }
    )
    def get_actionCapabilities(self, obj):
        request = self.context.get("request")
        user = getattr(request, "user", None)
        is_active = obj.status == CodeArtifact.Status.ACTIVE
        has_download = bool(
            obj.archive_file_id
            or obj.versions.filter(status=CodeArtifactVersion.Status.ACTIVE).exists()
        )
        if self.context.get("shared_section"):
            can_manage = can_manage_shared_code_artifact(user, obj)
        else:
            can_manage = can_manage_code_artifact(user, obj)
        return {
            "canView": is_active,
            "canDownload": is_active and has_download,
            "canRename": can_manage,
            "canDelete": can_manage,
        }

    def get_boundaryType(self, obj) -> str:
        classification = classify_workspace_record(obj)
        if classification.boundary_type == "pending_review":
            return "project_material"
        return classification.boundary_type

    def get_sourceProject(self, obj):
        return source_project_payload(obj)


class CodeArtifactCreateSerializer(serializers.Serializer):
    name = serializers.CharField(max_length=255)
    description = serializers.CharField(required=False, allow_blank=True)
    tags = serializers.ListField(child=serializers.CharField(), required=False)
    sourcePathLabel = serializers.CharField(required=False, allow_blank=True)
    visibility = serializers.ChoiceField(choices=CodeArtifact.Visibility.values, required=False)

    def to_internal_value(self, data):
        attrs = super().to_internal_value(data)
        attrs["source_path_label"] = attrs.pop("sourcePathLabel", "")
        return attrs


class CodeArtifactRenameSerializer(serializers.Serializer):
    name = serializers.CharField(max_length=255, trim_whitespace=True)
    reason = serializers.CharField(required=False, allow_blank=True, trim_whitespace=True)


class CodeUploadPolicySerializer(serializers.Serializer):
    category = serializers.CharField()
    maxSizeBytes = serializers.IntegerField(min_value=0)
    displayLabel = serializers.CharField()
    allowedExtensions = serializers.ListField(child=serializers.CharField())
    contentTypes = serializers.ListField(child=serializers.CharField())


def _split_string_list(value) -> list[str]:
    if value is None:
        return []
    if isinstance(value, list):
        return [str(item).strip() for item in value if str(item).strip()]
    return [item.strip() for item in str(value).split(",") if item.strip()]


class CodeArtifactUploadSerializer(serializers.Serializer):
    archive = serializers.FileField()
    name = serializers.CharField(max_length=255)
    description = serializers.CharField(allow_blank=False, trim_whitespace=True)
    tags = serializers.CharField(required=False, allow_blank=True)
    visibility = serializers.ChoiceField(
        choices=CodeArtifact.Visibility.values,
        required=False,
        default=CodeArtifact.Visibility.PROJECT_MEMBERS,
    )

    def to_internal_value(self, data):
        attrs = super().to_internal_value(data)
        attrs["upload"] = attrs.pop("archive")
        attrs["tags"] = _split_string_list(attrs.get("tags"))
        return attrs


class CodeArtifactVersionCreateSerializer(serializers.Serializer):
    versionLabel = serializers.CharField(required=False, allow_blank=True)
    commitReference = serializers.CharField(required=False, allow_blank=True)
    releaseNotes = serializers.CharField(required=False, allow_blank=True)
    description = serializers.CharField(required=False, allow_blank=True)
    sourceType = serializers.ChoiceField(
        choices=["local_folder", "local_archive"], required=False, default="local_archive"
    )
    sourcePathLabel = serializers.CharField(required=False, allow_blank=True)
    relativePathManifest = serializers.ListField(child=serializers.CharField(), required=False)
    filename = serializers.CharField(max_length=255)
    contentType = serializers.CharField(
        required=False, allow_blank=True, default="application/octet-stream"
    )
    sizeBytes = serializers.IntegerField(required=False, min_value=0, default=0)
    checksumSha256 = serializers.CharField(max_length=64)

    def to_internal_value(self, data):
        attrs = super().to_internal_value(data)
        attrs["version_label"] = attrs.pop("versionLabel", "")
        attrs["commit_reference"] = attrs.pop("commitReference", "")
        attrs["release_notes"] = attrs.pop("releaseNotes", "")
        attrs["source_type"] = attrs.pop("sourceType", "local_archive")
        attrs["source_path_label"] = attrs.pop("sourcePathLabel", "")
        attrs["relative_path_manifest"] = attrs.pop("relativePathManifest", [])
        attrs["content_type"] = attrs.pop("contentType", "application/octet-stream")
        attrs["size_bytes"] = attrs.pop("sizeBytes", 0)
        attrs["checksum_sha256"] = attrs.pop("checksumSha256")
        return attrs
