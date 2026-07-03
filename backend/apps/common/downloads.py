from django.utils import timezone

from apps.audit.models import DownloadEvent
from apps.audit.services import record_event
from apps.common.project_scope import can_access_asset
from apps.library.models import PaperAttachment, PaperRecord
from apps.repositories.models import CodeArtifact, CodeArtifactVersion


def _require_active_member(user, project):
    if not project.memberships.filter(user=user, status="active").exists():
        raise PermissionError("You are not authorized to download this file")


def _descriptor(filename: str) -> dict:
    return {
        "filename": filename,
        "deliveryMode": "direct_response",
        "url": "",
        "expiresAt": timezone.now().isoformat().replace("+00:00", "Z"),
    }


def describe_paper_download(user, paper: PaperRecord) -> dict:
    if getattr(paper, "uploaded_file_id", None):
        return describe_uploaded_file_download(
            user,
            paper.uploaded_file,
            project=paper.project,
            visibility=paper.visibility,
            asset_type="paper",
        )
    if not can_access_asset(user, project=paper.project, visibility=paper.visibility):
        raise PermissionError("You are not authorized to download this file")
    attachment = paper.attachments.filter(status=PaperAttachment.Status.ACTIVE).first()
    if attachment is None:
        raise PermissionError("No active attachment is available for this paper")
    event = DownloadEvent.objects.create(
        project=paper.project,
        actor=user,
        target_type="paper_attachment",
        target_id=str(attachment.id),
        filename=attachment.filename,
        checksum_sha256=attachment.checksum_sha256,
        delivery_mode=DownloadEvent.DeliveryMode.DIRECT_RESPONSE,
    )
    record_event(
        paper.project,
        user,
        "paper.downloaded",
        f"Downloaded paper attachment {attachment.id}",
        event,
    )
    return _descriptor(attachment.filename)


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
    return _descriptor(version.filename)


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


def describe_uploaded_file_download(
    user,
    uploaded_file,
    *,
    project,
    visibility: str,
    asset_type: str,
) -> dict:
    if not can_access_asset(user, project=project, visibility=visibility):
        raise PermissionError("You are not authorized to download this file")
    event = DownloadEvent.objects.create(
        project=project,
        actor=user,
        target_type=f"{asset_type}_uploaded_file",
        target_id=str(uploaded_file.id),
        filename=uploaded_file.original_filename,
        checksum_sha256=uploaded_file.checksum_sha256,
        delivery_mode=DownloadEvent.DeliveryMode.DIRECT_RESPONSE,
    )
    record_event(
        project,
        user,
        f"{asset_type}.downloaded",
        f"Downloaded {asset_type} file {uploaded_file.id}",
        event,
    )
    return _descriptor(uploaded_file.original_filename)
