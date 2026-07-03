from django.core.exceptions import PermissionDenied, ValidationError
from django.db import transaction
from django.utils import timezone

from apps.audit.services import record_event, record_upload
from apps.common.file_services import store_uploaded_file
from apps.common.models import UploadedFile
from apps.projects.archive_services import ensure_project_writable

from .models import DocumentCategory, DocumentRecord


def _can_manage_documents(user) -> bool:
    return bool(
        getattr(user, "is_superuser", False)
        or getattr(user, "is_administrator", False)
        or getattr(user, "is_advisor", False)
    )


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
        title: str,
        category_id: int,
        description: str = "",
        visibility: str = DocumentRecord.Visibility.PROJECT_MEMBERS,
    ) -> DocumentRecord:
        self._require_member()
        ensure_project_writable(self.project)
        if visibility == DocumentRecord.Visibility.GROUP_WIDE and not _can_manage_documents(
            self.user
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
            title=title,
            description=description,
            document_file=uploaded_file,
            checksum_sha256=uploaded_file.checksum_sha256,
            created_by=self.user,
        )
        record_upload(self.project, self.user, document, "document")
        return document
