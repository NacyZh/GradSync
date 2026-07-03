import hashlib
from pathlib import PurePath
from uuid import uuid4

from django.core.files.storage import default_storage

from .models import UploadedFile
from .upload_policy import validate_upload


def checksum_sha256(upload) -> str:
    digest = hashlib.sha256()
    position = upload.tell() if hasattr(upload, "tell") else None
    for chunk in upload.chunks():
        digest.update(chunk)
    if position is not None:
        upload.seek(position)
    return digest.hexdigest()


def store_uploaded_file(*, upload, category: str, owner) -> UploadedFile:
    policy = validate_upload(upload, category)
    checksum = checksum_sha256(upload)
    stored_name = f"collaboration/{policy.category}/{uuid4().hex}{policy.extension}"
    default_storage.save(stored_name, upload)
    return UploadedFile.objects.create(
        owner=owner,
        category=policy.category,
        original_filename=PurePath(policy.filename).name,
        stored_name=stored_name,
        content_type=policy.content_type,
        size_bytes=policy.size_bytes,
        checksum_sha256=checksum,
    )
