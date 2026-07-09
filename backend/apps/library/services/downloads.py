from apps.audit.models import DownloadEvent
from apps.audit.services import record_event
from apps.common.downloads import (
    DownloadUnavailable,
    describe_uploaded_file_download,
    download_descriptor,
)
from apps.common.project_scope import can_access_asset

from ..models import DocumentRecord, PaperAttachment, PaperRecord
from .papers import (
    PaperDownloadUnavailable,
    PreparedSharedPaperDownload,
    canonical_paper_download_filename,
    describe_shared_paper_download,
    paper_download_response_metadata,
    prepare_shared_paper_download,
)


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
    return download_descriptor(attachment.filename)


def describe_document_download(user, document: DocumentRecord) -> dict:
    if document.status != DocumentRecord.Status.ACTIVE:
        raise DownloadUnavailable("Document is no longer available")
    if not document.document_file_id:
        raise DownloadUnavailable("No file is available for this document")
    return describe_uploaded_file_download(
        user,
        document.document_file,
        project=document.project,
        visibility=document.visibility,
        asset_type="document",
    )


__all__ = [
    "DownloadUnavailable",
    "PaperDownloadUnavailable",
    "PreparedSharedPaperDownload",
    "canonical_paper_download_filename",
    "describe_document_download",
    "describe_paper_download",
    "describe_shared_paper_download",
    "paper_download_response_metadata",
    "prepare_shared_paper_download",
]
