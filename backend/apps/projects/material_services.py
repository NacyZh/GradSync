from __future__ import annotations

from dataclasses import dataclass

from django.core.exceptions import PermissionDenied, ValidationError
from django.db import transaction
from django.db.models import Q
from django.utils import timezone

from apps.audit.boundary_events import record_boundary_event
from apps.common.downloads import DownloadUnavailable
from apps.common.file_services import store_uploaded_file
from apps.common.models import UploadedFile
from apps.library.models.documents import DocumentCategory, DocumentRecord
from apps.library.models.papers import PaperRecord
from apps.repositories.models import CodeArtifact, CodeArtifactVersion

from .archive_services import ensure_project_writable
from .models import ProjectMaterial
from .permissions import (
    can_access_project_only_material,
    can_change_project_material_visibility,
)


class BoundaryClassification:
    STANDALONE_SHARED = "standalone_shared"
    PROJECT_MATERIAL = "project_material"
    PENDING_REVIEW = "pending_review"


@dataclass(frozen=True)
class WorkspaceRecordClassification:
    boundary_type: str
    visibility: str
    source_project_id: int | None
    pending_review: bool
    reason: str


def classify_workspace_record(record) -> WorkspaceRecordClassification:
    boundary = getattr(
        record,
        "boundary_classification",
        BoundaryClassification.STANDALONE_SHARED,
    )
    source_project = getattr(record, "source_project", None) or getattr(record, "project", None)
    reason = getattr(record, "classification_reason", "") or "previous_functional_area"
    if boundary == BoundaryClassification.PENDING_REVIEW:
        return WorkspaceRecordClassification(
            boundary_type=BoundaryClassification.PENDING_REVIEW,
            visibility=getattr(record, "visibility", "project_members"),
            source_project_id=getattr(source_project, "id", None),
            pending_review=True,
            reason=reason,
        )
    if boundary == BoundaryClassification.PROJECT_MATERIAL:
        return WorkspaceRecordClassification(
            boundary_type=BoundaryClassification.PROJECT_MATERIAL,
            visibility=getattr(record, "visibility", "project_members"),
            source_project_id=getattr(source_project, "id", None),
            pending_review=False,
            reason=reason,
        )
    return WorkspaceRecordClassification(
        boundary_type=BoundaryClassification.STANDALONE_SHARED,
        visibility="group_wide",
        source_project_id=getattr(source_project, "id", None)
        if getattr(record, "source_project_id", None)
        else None,
        pending_review=False,
        reason=reason,
    )


def is_externally_shared_record(record) -> bool:
    classification = classify_workspace_record(record)
    if classification.pending_review:
        return False
    if classification.boundary_type == BoundaryClassification.STANDALONE_SHARED:
        return True
    return (
        classification.boundary_type == BoundaryClassification.PROJECT_MATERIAL
        and getattr(record, "visibility", "") == "group_wide"
    )


def externally_shared_q(boundary_field="boundary_classification", visibility_field="visibility"):
    return Q(**{boundary_field: BoundaryClassification.STANDALONE_SHARED}) | Q(
        **{
            boundary_field: BoundaryClassification.PROJECT_MATERIAL,
            visibility_field: "group_wide",
        }
    )


def source_project_payload(record):
    source_project = getattr(record, "source_project", None)
    if source_project is None:
        return None
    return {
        "id": str(source_project.id),
        "title": source_project.title,
    }


def _record_visibility(material_visibility: str) -> str:
    if material_visibility == ProjectMaterial.VisibilityState.GROUP_WIDE:
        return "group_wide"
    return "project_members"


def _material_visibility(record_visibility: str) -> str:
    if record_visibility == "group_wide":
        return ProjectMaterial.VisibilityState.GROUP_WIDE
    return ProjectMaterial.VisibilityState.PROJECT_ONLY


def _require_project_member_or_admin(user, project) -> None:
    if not can_access_project_only_material(user, project):
        raise PermissionDenied("You are not authorized to access project materials")


def project_material_queryset_for(user, project):
    _require_project_member_or_admin(user, project)
    return ProjectMaterial.objects.filter(source_project=project).select_related(
        "source_project", "created_by"
    )


def _default_document_category(user) -> DocumentCategory:
    category, _ = DocumentCategory.objects.get_or_create(
        name="Project Materials",
        defaults={"description": "Project-owned shared documents", "created_by": user},
    )
    return category


def _create_backing_record(
    *,
    user,
    project,
    material_type: str,
    upload,
    title: str,
    visibility: str,
):
    record_visibility = _record_visibility(visibility)
    uploaded_file = store_uploaded_file(
        upload=upload,
        category={
            ProjectMaterial.MaterialType.PAPER: UploadedFile.Category.PAPER,
            ProjectMaterial.MaterialType.DOCUMENT: UploadedFile.Category.DOCUMENT,
            ProjectMaterial.MaterialType.CODE: UploadedFile.Category.CODE,
        }[material_type],
        owner=user,
    )
    common = {
        "project": project,
        "visibility": record_visibility,
        "visibility_changed_by": user,
        "visibility_changed_at": timezone.now(),
        "boundary_classification": BoundaryClassification.PROJECT_MATERIAL,
        "source_project": project,
        "classification_reason": "explicit_project_specific",
        "created_by": user,
    }
    cleaned_title = title.strip() if title else uploaded_file.original_filename
    if material_type == ProjectMaterial.MaterialType.DOCUMENT:
        return DocumentRecord.objects.create(
            **common,
            category=_default_document_category(user),
            title=cleaned_title,
            description="",
            document_file=uploaded_file,
            checksum_sha256=uploaded_file.checksum_sha256,
        )
    if material_type == ProjectMaterial.MaterialType.CODE:
        artifact = CodeArtifact.objects.create(
            **common,
            name=cleaned_title,
            description="Project material code archive",
            tags=[],
            source_path_label=uploaded_file.original_filename,
            archive_file=uploaded_file,
            checksum_sha256=uploaded_file.checksum_sha256,
        )
        CodeArtifactVersion.objects.create(
            artifact=artifact,
            project=project,
            storage_key=uploaded_file.stored_name,
            filename=uploaded_file.original_filename,
            relative_path_manifest=[uploaded_file.original_filename],
            content_type=uploaded_file.content_type,
            size_bytes=uploaded_file.size_bytes,
            checksum_sha256=uploaded_file.checksum_sha256,
            imported_by=user,
        )
        return artifact
    if material_type == ProjectMaterial.MaterialType.PAPER:
        return PaperRecord.objects.create(
            **common,
            title=cleaned_title,
            uploaded_file=uploaded_file,
            checksum_sha256=uploaded_file.checksum_sha256,
            import_source=PaperRecord.ImportSource.LOCAL_FILE,
        )
    raise ValidationError("Unsupported project material type")


def backing_record_for(material: ProjectMaterial):
    models = {
        ProjectMaterial.MaterialType.PAPER: PaperRecord,
        ProjectMaterial.MaterialType.DOCUMENT: DocumentRecord,
        ProjectMaterial.MaterialType.CODE: CodeArtifact,
    }
    model = models.get(material.material_type)
    return model.objects.filter(pk=material.backing_record_id).first() if model else None


def project_material_display_name(material: ProjectMaterial) -> str:
    record = backing_record_for(material)
    if record is None:
        return ""
    return getattr(record, "title", "") or getattr(record, "name", "") or ""


def project_material_download_available(material: ProjectMaterial) -> bool:
    if material.classification_state != ProjectMaterial.ClassificationState.ACTIVE:
        return False
    record = backing_record_for(material)
    if record is None:
        return False
    if material.material_type == ProjectMaterial.MaterialType.DOCUMENT:
        return bool(getattr(record, "document_file_id", None))
    if material.material_type == ProjectMaterial.MaterialType.PAPER:
        return bool(
            getattr(record, "uploaded_file_id", None)
            or record.attachments.filter(status="active").exists()
        )
    if material.material_type == ProjectMaterial.MaterialType.CODE:
        return bool(
            getattr(record, "archive_file_id", None)
            or record.versions.filter(storage_key__gt="").exists()
        )
    return False


def project_material_capabilities(user, material: ProjectMaterial) -> dict:
    can_change = can_change_project_material_visibility(user, material.source_project)
    return {
        "canView": True,
        "canDownload": project_material_download_available(material),
        "canRename": False,
        "canDelete": False,
        "canChangeVisibility": can_change,
    }


def describe_project_material_download(user, material: ProjectMaterial) -> dict:
    _require_project_member_or_admin(user, material.source_project)
    record = backing_record_for(material)
    if record is None or not project_material_download_available(material):
        raise DownloadUnavailable("Project material is no longer available")
    if material.material_type == ProjectMaterial.MaterialType.DOCUMENT:
        from apps.library.services.downloads import describe_document_download

        return describe_document_download(user, record)
    if material.material_type == ProjectMaterial.MaterialType.PAPER:
        from apps.library.services.downloads import describe_paper_download

        return describe_paper_download(user, record)
    if material.material_type == ProjectMaterial.MaterialType.CODE:
        from apps.repositories.download_services import describe_code_artifact_download

        return describe_code_artifact_download(user, record)
    raise DownloadUnavailable("Project material is no longer available")


@transaction.atomic
def create_project_material(
    *,
    user,
    project,
    material_type: str,
    upload,
    title: str = "",
    visibility: str = ProjectMaterial.VisibilityState.PROJECT_ONLY,
) -> ProjectMaterial:
    _require_project_member_or_admin(user, project)
    ensure_project_writable(project)
    if visibility == ProjectMaterial.VisibilityState.GROUP_WIDE and not (
        can_change_project_material_visibility(user, project)
    ):
        record_boundary_event(
            actor=user,
            resource=None,
            boundary_type="project_material",
            visibility_state=visibility,
            source_project=project,
            action="visibility_change",
            outcome="denied",
        )
        raise PermissionDenied("Only project advisors and administrators can share group-wide")
    if material_type not in ProjectMaterial.MaterialType.values:
        raise ValidationError("Unsupported project material type")
    if upload is None:
        raise ValidationError("A project material file is required")

    record = _create_backing_record(
        user=user,
        project=project,
        material_type=material_type,
        upload=upload,
        title=title,
        visibility=visibility,
    )
    material = ProjectMaterial.objects.create(
        source_project=project,
        material_type=material_type,
        backing_record_id=record.id,
        visibility_state=visibility,
        classification_state=ProjectMaterial.ClassificationState.ACTIVE,
        classification_reason=ProjectMaterial.ClassificationReason.EXPLICIT_PROJECT_SPECIFIC,
        visibility_changed_by=user,
        visibility_changed_at=timezone.now(),
        created_by=user,
    )
    record_boundary_event(
        actor=user,
        resource=material,
        boundary_type="project_material",
        visibility_state=visibility,
        source_project=project,
        action="create",
        outcome="success",
        metadata={"materialType": material_type, "backingRecordId": record.id},
    )
    return material


@transaction.atomic
def change_project_material_visibility(
    *,
    user,
    material: ProjectMaterial,
    visibility: str,
    reason: str = "",
) -> ProjectMaterial:
    if not can_change_project_material_visibility(user, material.source_project):
        record_boundary_event(
            actor=user,
            resource=None,
            boundary_type="project_material",
            visibility_state=visibility,
            source_project=material.source_project,
            action="visibility_change",
            outcome="denied",
            metadata={"materialId": material.id},
        )
        raise PermissionDenied("Only project advisors and administrators can change visibility")
    if visibility not in ProjectMaterial.VisibilityState.values:
        raise ValidationError("Unsupported visibility")

    material.visibility_state = visibility
    material.visibility_changed_by = user
    material.visibility_changed_at = timezone.now()
    material.save(
        update_fields=[
            "visibility_state",
            "visibility_changed_by",
            "visibility_changed_at",
            "updated_at",
        ]
    )
    record = backing_record_for(material)
    if record is not None:
        record.visibility = _record_visibility(visibility)
        record.visibility_changed_by = user
        record.visibility_changed_at = material.visibility_changed_at
        record.boundary_classification = BoundaryClassification.PROJECT_MATERIAL
        record.source_project = material.source_project
        record.save(
            update_fields=[
                "visibility",
                "visibility_changed_by",
                "visibility_changed_at",
                "boundary_classification",
                "source_project",
                "updated_at",
            ]
        )
    record_boundary_event(
        actor=user,
        resource=material,
        boundary_type="project_material",
        visibility_state=visibility,
        source_project=material.source_project,
        action="visibility_change",
        outcome="success",
        metadata={"reason": reason} if reason else None,
    )
    return material
