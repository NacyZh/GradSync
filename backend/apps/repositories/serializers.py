from rest_framework import serializers

from .models import CodeArtifact, CodeArtifactVersion


class CodeArtifactVersionSerializer(serializers.ModelSerializer):
    artifactId = serializers.CharField(source="artifact_id", read_only=True)
    projectId = serializers.CharField(source="project_id", read_only=True)
    versionLabel = serializers.CharField(source="version_label", read_only=True)
    commitReference = serializers.CharField(source="commit_reference", read_only=True)
    releaseNotes = serializers.CharField(source="release_notes", read_only=True)
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
            "filename",
            "contentType",
            "sizeBytes",
            "checksumSha256",
            "status",
        ]


class CodeArtifactSerializer(serializers.ModelSerializer):
    projectId = serializers.CharField(source="project_id", read_only=True)
    latestVersion = serializers.SerializerMethodField()

    class Meta:
        model = CodeArtifact
        fields = ["id", "projectId", "name", "description", "tags", "status", "latestVersion"]

    def get_latestVersion(self, obj):
        version = obj.versions.first()
        return CodeArtifactVersionSerializer(version).data if version else None


class CodeArtifactCreateSerializer(serializers.Serializer):
    name = serializers.CharField(max_length=255)
    description = serializers.CharField(required=False, allow_blank=True)
    tags = serializers.ListField(child=serializers.CharField(), required=False)


class CodeArtifactVersionCreateSerializer(serializers.Serializer):
    versionLabel = serializers.CharField(required=False, allow_blank=True)
    commitReference = serializers.CharField(required=False, allow_blank=True)
    releaseNotes = serializers.CharField(required=False, allow_blank=True)
    filename = serializers.CharField(max_length=255)
    contentType = serializers.CharField(required=False, allow_blank=True, default="application/octet-stream")
    sizeBytes = serializers.IntegerField(required=False, min_value=0, default=0)
    checksumSha256 = serializers.CharField(max_length=64)

    def to_internal_value(self, data):
        attrs = super().to_internal_value(data)
        attrs["version_label"] = attrs.pop("versionLabel", "")
        attrs["commit_reference"] = attrs.pop("commitReference", "")
        attrs["release_notes"] = attrs.pop("releaseNotes", "")
        attrs["content_type"] = attrs.pop("contentType", "application/octet-stream")
        attrs["size_bytes"] = attrs.pop("sizeBytes", 0)
        attrs["checksum_sha256"] = attrs.pop("checksumSha256")
        return attrs
