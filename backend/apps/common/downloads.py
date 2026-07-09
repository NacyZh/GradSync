from django.core.files.storage import default_storage
from django.http import FileResponse
from django.utils import timezone

from apps.audit.models import DownloadEvent
from apps.audit.services import record_event
from apps.common.project_scope import can_access_asset


class DownloadUnavailable(Exception):
    pass


def download_descriptor(filename: str) -> dict:
    return {
        "filename": filename,
        "deliveryMode": "direct_response",
        "url": "",
        "expiresAt": timezone.now().isoformat().replace("+00:00", "Z"),
    }


def storage_file_download_response(
    storage_key: str,
    *,
    filename: str,
    content_type: str = "application/octet-stream",
) -> FileResponse:
    return FileResponse(
        default_storage.open(storage_key, "rb"),
        as_attachment=True,
        filename=filename,
        content_type=content_type,
    )


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
    return download_descriptor(uploaded_file.original_filename)
