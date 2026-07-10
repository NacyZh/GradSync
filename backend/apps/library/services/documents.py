from dataclasses import dataclass

from django.core.exceptions import PermissionDenied, ValidationError
from django.core.files.storage import default_storage
from django.db import transaction
from django.db.models import Q
from django.utils import timezone

from apps.audit.services import record_event, record_upload
from apps.common.file_services import store_uploaded_file
from apps.common.models import UploadedFile
from apps.common.project_scope import visible_asset_q
from apps.projects.archive_services import ensure_project_writable
from apps.projects.material_services import externally_shared_q
from apps.projects.models import ResearchProject
from apps.projects.permissions import is_active_user

from ..models import DocumentCategory, DocumentRecord

SEEDED_DOCUMENT_EXAMPLE_TITLE = "Example Protocol"
SEEDED_DOCUMENT_EXAMPLE_CATEGORY = "Protocols"
SEEDED_DOCUMENT_EXAMPLE_ORIGINAL_FILENAME = "example-protocol.pdf"
SEEDED_DOCUMENT_EXAMPLE_STORED_NAME = "e2e/example-protocol.pdf"
SEEDED_DOCUMENT_EXAMPLE_CHECKSUM_SHA256 = "d" * 64
SEEDED_DOCUMENT_EXAMPLE_IDENTITIES = (
    {
        "title": SEEDED_DOCUMENT_EXAMPLE_TITLE,
        "category_name": SEEDED_DOCUMENT_EXAMPLE_CATEGORY,
        "original_filename": SEEDED_DOCUMENT_EXAMPLE_ORIGINAL_FILENAME,
        "stored_name": SEEDED_DOCUMENT_EXAMPLE_STORED_NAME,
        "checksum_sha256": SEEDED_DOCUMENT_EXAMPLE_CHECKSUM_SHA256,
    },
)


@dataclass(frozen=True)
class SeededDocumentCleanupResult:
    matched: int
    removed: int


def _can_manage_documents(user) -> bool:
    return bool(
        getattr(user, "is_superuser", False)
        or getattr(user, "is_administrator", False)
        or getattr(user, "is_advisor", False)
    )


def can_manage_document(user, project) -> bool:
    if not user or not getattr(user, "is_authenticated", False):
        return False
    if getattr(user, "is_superuser", False) or getattr(user, "is_administrator", False):
        return True
    return project.advisor_id == getattr(user, "id", None)


def safe_document_title_from_filename(filename: str) -> str:
    basename = str(filename or "").replace("\\", "/").split("/")[-1]
    safe = "".join(char if char.isalnum() or char in " ._-" else " " for char in basename)
    safe = " ".join(safe.split()).strip(" ._-")
    if not safe:
        return "Untitled document"
    return safe[:255]


def active_document_queryset(user, project):
    return (
        DocumentRecord.objects.filter(project=project, status=DocumentRecord.Status.ACTIVE)
        .filter(visible_asset_q(user))
        .select_related("category", "document_file", "project")
        .distinct()
    )


def default_shared_anchor_project_for(user) -> ResearchProject | None:
    queryset = ResearchProject.objects.filter(status=ResearchProject.Status.ACTIVE)
    if getattr(user, "is_superuser", False) or getattr(user, "is_administrator", False):
        return queryset.order_by("id").first()
    return (
        queryset.filter(Q(advisor=user) | Q(memberships__user=user, memberships__status="active"))
        .distinct()
        .order_by("id")
        .first()
    )


def shared_document_queryset_for(user):
    if not is_active_user(user):
        raise PermissionDenied("Active account required for the shared document library.")
    return (
        DocumentRecord.objects.filter(status=DocumentRecord.Status.ACTIVE)
        .filter(externally_shared_q())
        .select_related("category", "document_file", "project", "source_project")
        .distinct()
    )


def document_action_capabilities(user, document: DocumentRecord) -> dict:
    is_active = document.status == DocumentRecord.Status.ACTIVE
    can_manage = is_active and can_manage_document(user, document.project)
    return {
        "canView": is_active,
        "canDownload": is_active and bool(document.document_file_id),
        "canRename": can_manage,
        "canDelete": can_manage,
        "canUploadGroupWide": can_manage_document(user, document.project),
    }


def record_rejected_document_management_attempt(project, actor, document, action: str):
    return record_event(
        project,
        actor,
        f"document.{action}.rejected",
        f"Rejected document {action} for {getattr(document, 'id', '')}",
        document,
    )


def is_seeded_document_example(document: DocumentRecord) -> bool:
    uploaded_file = document.document_file
    return any(
        document.title == identity["title"]
        and document.category.name == identity["category_name"]
        and uploaded_file.original_filename == identity["original_filename"]
        and uploaded_file.stored_name == identity["stored_name"]
        and document.checksum_sha256 == identity["checksum_sha256"]
        and uploaded_file.checksum_sha256 == identity["checksum_sha256"]
        for identity in SEEDED_DOCUMENT_EXAMPLE_IDENTITIES
    )


def cleanup_seeded_library_documents(*, dry_run: bool = False) -> SeededDocumentCleanupResult:
    candidates = (
        DocumentRecord.objects.filter(
            title__in=[identity["title"] for identity in SEEDED_DOCUMENT_EXAMPLE_IDENTITIES],
            category__name__in=[
                identity["category_name"] for identity in SEEDED_DOCUMENT_EXAMPLE_IDENTITIES
            ],
            checksum_sha256__in=[
                identity["checksum_sha256"] for identity in SEEDED_DOCUMENT_EXAMPLE_IDENTITIES
            ],
        )
        .select_related("category", "document_file")
    )
    matched = [document for document in candidates if is_seeded_document_example(document)]
    if dry_run:
        return SeededDocumentCleanupResult(matched=len(matched), removed=0)

    storage_keys = [document.document_file.stored_name for document in matched]
    uploaded_files = [document.document_file for document in matched]
    with transaction.atomic():
        removed = 0
        for document in matched:
            document.delete()
            removed += 1
        for uploaded_file in uploaded_files:
            uploaded_file.delete()
    for storage_key in dict.fromkeys(storage_keys):
        if storage_key and default_storage.exists(storage_key):
            default_storage.delete(storage_key)
    return SeededDocumentCleanupResult(matched=len(matched), removed=removed)


def _normalized_document_title(title: str) -> str:
    return " ".join(title.strip().casefold().split())


class DocumentCategoryService:
    def __init__(self, user):
        self.user = user

    def create_category(self, *, name: str, description: str = "") -> DocumentCategory:
        if not _can_manage_documents(self.user):
            raise PermissionDenied(
                "Only teachers and administrators can create document categories"
            )
        normalized_name = name.strip()
        if DocumentCategory.objects.filter(name__iexact=normalized_name).exists():
            raise ValidationError("Document category already exists")
        category = DocumentCategory.objects.create(
            name=normalized_name,
            description=description,
            created_by=self.user,
        )
        record_event(
            None,
            self.user,
            "document_category.created",
            f"Created document category {category.name}",
            category,
        )
        return category


class DocumentService:
    def __init__(self, user, project):
        self.user = user
        self.project = project

    def _require_member(self):
        if not self.project.memberships.filter(user=self.user, status="active").exists():
            raise ValidationError("You are not a member of this project")

    @transaction.atomic
    def upload_document(
        self,
        *,
        upload,
        title: str = "",
        category_id: int,
        description: str = "",
        visibility: str = DocumentRecord.Visibility.PROJECT_MEMBERS,
    ) -> DocumentRecord:
        self._require_member()
        ensure_project_writable(self.project)
        if visibility == DocumentRecord.Visibility.GROUP_WIDE and not can_manage_document(
            self.user, self.project
        ):
            raise PermissionDenied(
                "Only teachers and administrators can share documents group-wide"
            )
        category = DocumentCategory.objects.filter(
            pk=category_id, status=DocumentCategory.Status.ACTIVE
        ).first()
        if category is None:
            raise ValidationError("Document category is required")

        uploaded_file = store_uploaded_file(
            upload=upload,
            category=UploadedFile.Category.DOCUMENT,
            owner=self.user,
        )
        document = DocumentRecord.objects.create(
            project=self.project,
            visibility=visibility or DocumentRecord.Visibility.PROJECT_MEMBERS,
            visibility_changed_by=self.user,
            visibility_changed_at=timezone.now(),
            category=category,
            title=title.strip() or safe_document_title_from_filename(upload.name),
            description=description,
            document_file=uploaded_file,
            checksum_sha256=uploaded_file.checksum_sha256,
            created_by=self.user,
        )
        record_upload(self.project, self.user, document, "document")
        return document

    @transaction.atomic
    def upload_standalone_document(
        self,
        *,
        upload,
        title: str = "",
        category_id: int,
        description: str = "",
    ) -> DocumentRecord:
        if not is_active_user(self.user):
            raise PermissionDenied("Active account required for the shared document library.")
        anchor_project = self.project or default_shared_anchor_project_for(self.user)
        if anchor_project is None:
            raise ValidationError("A workspace project is required before uploading documents")
        category = DocumentCategory.objects.filter(
            pk=category_id, status=DocumentCategory.Status.ACTIVE
        ).first()
        if category is None:
            raise ValidationError("Document category is required")

        uploaded_file = store_uploaded_file(
            upload=upload,
            category=UploadedFile.Category.DOCUMENT,
            owner=self.user,
        )
        document = DocumentRecord.objects.create(
            project=anchor_project,
            visibility=DocumentRecord.Visibility.GROUP_WIDE,
            visibility_changed_by=self.user,
            visibility_changed_at=timezone.now(),
            boundary_classification=DocumentRecord.BoundaryClassification.STANDALONE_SHARED,
            source_project=None,
            classification_reason=DocumentRecord.ClassificationReason.PREVIOUS_FUNCTIONAL_AREA,
            category=category,
            title=title.strip() or safe_document_title_from_filename(upload.name),
            description=description,
            document_file=uploaded_file,
            checksum_sha256=uploaded_file.checksum_sha256,
            created_by=self.user,
        )
        record_upload(anchor_project, self.user, document, "document")
        return document

    def rename_document(
        self,
        document: DocumentRecord,
        *,
        newTitle: str,
        reason: str = "",
    ) -> DocumentRecord:
        ensure_project_writable(self.project)
        if document.project_id != self.project.id:
            raise ValidationError("Document does not belong to this project")
        if document.status != DocumentRecord.Status.ACTIVE:
            raise ValidationError("Document is no longer active")
        if not can_manage_document(self.user, self.project):
            record_rejected_document_management_attempt(
                self.project, self.user, document, "rename"
            )
            raise PermissionDenied("You cannot rename this document")

        cleaned_title = newTitle.strip()
        if not cleaned_title:
            raise ValidationError("Document title is required")
        normalized_title = _normalized_document_title(cleaned_title)
        duplicate_exists = any(
            _normalized_document_title(candidate.title) == normalized_title
            for candidate in DocumentRecord.objects.filter(
                project=self.project,
                category=document.category,
                status=DocumentRecord.Status.ACTIVE,
            ).exclude(pk=document.pk)
        )
        if duplicate_exists:
            raise ValidationError("Active document title already exists in this category")

        with transaction.atomic():
            document.title = cleaned_title
            document.save(update_fields=["title", "updated_at"])
            summary = f"Renamed document {document.id}"
            if reason:
                summary = f"{summary}: {reason}"
            record_event(self.project, self.user, "document.renamed", summary, document)
        return document

    def archive_document(self, document: DocumentRecord, *, reason: str = "") -> None:
        ensure_project_writable(self.project)
        if document.project_id != self.project.id:
            raise ValidationError("Document does not belong to this project")
        if document.status != DocumentRecord.Status.ACTIVE:
            raise ValidationError("Document is no longer active")
        if not can_manage_document(self.user, self.project):
            record_rejected_document_management_attempt(
                self.project, self.user, document, "delete"
            )
            raise PermissionDenied("You cannot delete this document")

        with transaction.atomic():
            document.status = DocumentRecord.Status.ARCHIVED
            document.save(update_fields=["status", "updated_at"])
            summary = f"Deleted document {document.id}"
            if reason:
                summary = f"{summary}: {reason}"
            record_event(self.project, self.user, "document.deleted", summary, document)
