from django.utils import timezone

from apps.audit.models import DownloadEvent
from apps.audit.services import record_event
from apps.library.models import PaperAttachment, PaperRecord
from apps.repositories.models import CodeArtifactVersion


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
    _require_active_member(user, paper.project)
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
    _require_active_member(user, version.project)
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
