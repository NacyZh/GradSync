from apps.audit.models import DownloadEvent
from apps.audit.services import record_event
from apps.common.downloads import describe_uploaded_file_download, download_descriptor
from apps.common.project_scope import can_access_asset

from .models import CodeArtifact, CodeArtifactVersion


def describe_code_download(user, version: CodeArtifactVersion) -> dict:
    visibility = getattr(version.artifact, "visibility", "project_members")
    if not can_access_asset(user, project=version.project, visibility=visibility):
        raise PermissionError("You are not authorized to download this file")
    event = DownloadEvent.objects.create(
        project=version.project,
        actor=user,
        target_type="code_artifact_version",
        target_id=str(version.id),
        filename=version.filename,
        checksum_sha256=version.checksum_sha256,
        delivery_mode=DownloadEvent.DeliveryMode.DIRECT_RESPONSE,
    )
    record_event(
        version.project,
        user,
        "code_artifact_version.downloaded",
        f"Downloaded code artifact version {version.id}",
        event,
    )
    return download_descriptor(version.filename)


def describe_code_artifact_download(user, artifact: CodeArtifact) -> dict:
    if getattr(artifact, "archive_file_id", None):
        return describe_uploaded_file_download(
            user,
            artifact.archive_file,
            project=artifact.project,
            visibility=artifact.visibility,
            asset_type="code_artifact",
        )
    if not can_access_asset(user, project=artifact.project, visibility=artifact.visibility):
        raise PermissionError("You are not authorized to download this file")
    version = artifact.versions.filter(status=CodeArtifactVersion.Status.ACTIVE).first()
    if version is None:
        raise PermissionError("No active archive is available for this code artifact")
    return describe_code_download(user, version)
