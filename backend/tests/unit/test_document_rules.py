import pytest

from apps.common.models import UploadedFile
from apps.library import services as library_services
from apps.library.models import DocumentRecord
from apps.library.services.documents import (
    SEEDED_DOCUMENT_EXAMPLE_CHECKSUM_SHA256,
    SEEDED_DOCUMENT_EXAMPLE_ORIGINAL_FILENAME,
    SEEDED_DOCUMENT_EXAMPLE_STORED_NAME,
    SEEDED_DOCUMENT_EXAMPLE_TITLE,
    DocumentService,
    active_document_queryset,
    can_manage_document,
    document_action_capabilities,
    is_seeded_document_example,
    safe_document_title_from_filename,
)
from tests.factories.accounts import UserFactory
from tests.factories.collaboration import (
    DocumentCategoryFactory,
    ProjectMembershipFactory,
    ResearchProjectFactory,
    UploadedFileFactory,
    active_project_document,
    archived_project_document,
)


@pytest.mark.django_db
def test_document_maintainer_is_project_advisor_or_administrator():
    advisor = UserFactory(global_role="advisor", status="active")
    other_advisor = UserFactory(global_role="advisor", status="active")
    administrator = UserFactory(global_role="admin", status="active")
    student = UserFactory(global_role="student", status="active")
    project = ResearchProjectFactory(advisor=advisor)
    ProjectMembershipFactory(project=project, user=student)

    assert can_manage_document(advisor, project) is True
    assert can_manage_document(administrator, project) is True
    assert can_manage_document(student, project) is False
    assert can_manage_document(other_advisor, project) is False


def test_safe_document_title_from_filename_removes_paths_and_unsafe_characters():
    assert (
        safe_document_title_from_filename(r"C:\Users\ada\..\protocol <final>.pdf")
        == "protocol final .pdf"
    )
    assert safe_document_title_from_filename("../../") == "Untitled document"
    assert len(safe_document_title_from_filename("x" * 300 + ".pdf")) == 255


@pytest.mark.django_db
def test_active_document_queryset_excludes_archived_documents():
    advisor = UserFactory(global_role="advisor", status="active")
    project = ResearchProjectFactory(advisor=advisor)
    ProjectMembershipFactory(project=project, user=advisor, role="advisor")
    category = DocumentCategoryFactory(created_by=advisor)
    active = active_project_document(project=project, category=category, title="Active")
    archived_project_document(project=project, category=category, title="Archived")

    assert list(active_document_queryset(advisor, project)) == [active]


@pytest.mark.django_db
def test_document_action_capabilities_follow_active_file_and_maintainer_rules():
    advisor = UserFactory(global_role="advisor", status="active")
    student = UserFactory(global_role="student", status="active")
    project = ResearchProjectFactory(advisor=advisor)
    ProjectMembershipFactory(project=project, user=advisor, role="advisor")
    ProjectMembershipFactory(project=project, user=student)
    category = DocumentCategoryFactory(created_by=advisor)
    document = active_project_document(project=project, category=category, title="Protocol")

    assert document_action_capabilities(advisor, document) == {
        "canView": True,
        "canDownload": True,
        "canRename": True,
        "canDelete": True,
        "canUploadGroupWide": True,
    }
    assert document_action_capabilities(student, document) == {
        "canView": True,
        "canDownload": True,
        "canRename": False,
        "canDelete": False,
        "canUploadGroupWide": False,
    }

    document.status = DocumentRecord.Status.ARCHIVED
    assert document_action_capabilities(advisor, document)["canView"] is False

    document.status = DocumentRecord.Status.ACTIVE
    document.document_file = UploadedFileFactory(
        owner=advisor,
        category=UploadedFile.Category.DOCUMENT,
        original_filename="missing.pdf",
    )
    document.document_file_id = None
    assert document_action_capabilities(advisor, document)["canDownload"] is False


@pytest.mark.django_db
def test_document_service_rename_rejects_duplicate_category_titles_and_archived_documents():
    advisor = UserFactory(global_role="advisor", status="active")
    project = ResearchProjectFactory(advisor=advisor)
    ProjectMembershipFactory(project=project, user=advisor, role="advisor")
    category = DocumentCategoryFactory(created_by=advisor)
    document = active_project_document(project=project, category=category, title="Protocol A")
    active_project_document(project=project, category=category, title="Protocol B")
    service = DocumentService(advisor, project)

    with pytest.raises(Exception, match="already exists"):
        service.rename_document(document, newTitle=" protocol b ")

    document.status = DocumentRecord.Status.ARCHIVED
    document.save(update_fields=["status"])
    with pytest.raises(Exception, match="no longer active"):
        service.rename_document(document, newTitle="Protocol C")


@pytest.mark.django_db
def test_document_service_archive_rejects_already_archived_documents():
    advisor = UserFactory(global_role="advisor", status="active")
    project = ResearchProjectFactory(advisor=advisor)
    ProjectMembershipFactory(project=project, user=advisor, role="advisor")
    category = DocumentCategoryFactory(created_by=advisor)
    document = active_project_document(project=project, category=category, title="Protocol A")
    service = DocumentService(advisor, project)

    service.archive_document(document)
    document.refresh_from_db()

    assert document.status == DocumentRecord.Status.ARCHIVED
    with pytest.raises(Exception, match="no longer active"):
        service.archive_document(document)


@pytest.mark.django_db
def test_seeded_document_example_matcher_is_exact_and_preserves_similar_documents():
    advisor = UserFactory(global_role="advisor", status="active")
    project = ResearchProjectFactory(advisor=advisor)
    category = DocumentCategoryFactory(name="Protocols", created_by=advisor)
    exact_file = UploadedFileFactory(
        owner=advisor,
        category=UploadedFile.Category.DOCUMENT,
        original_filename=SEEDED_DOCUMENT_EXAMPLE_ORIGINAL_FILENAME,
        stored_name=SEEDED_DOCUMENT_EXAMPLE_STORED_NAME,
        checksum_sha256=SEEDED_DOCUMENT_EXAMPLE_CHECKSUM_SHA256,
    )
    exact = active_project_document(
        project=project,
        category=category,
        title=SEEDED_DOCUMENT_EXAMPLE_TITLE,
        document_file=exact_file,
        checksum_sha256=SEEDED_DOCUMENT_EXAMPLE_CHECKSUM_SHA256,
    )
    similar_file = UploadedFileFactory(
        owner=advisor,
        category=UploadedFile.Category.DOCUMENT,
        original_filename=SEEDED_DOCUMENT_EXAMPLE_ORIGINAL_FILENAME,
        stored_name="user/example-protocol.pdf",
        checksum_sha256=SEEDED_DOCUMENT_EXAMPLE_CHECKSUM_SHA256,
    )
    similar = active_project_document(
        project=project,
        category=category,
        title=SEEDED_DOCUMENT_EXAMPLE_TITLE,
        document_file=similar_file,
        checksum_sha256=SEEDED_DOCUMENT_EXAMPLE_CHECKSUM_SHA256,
    )

    assert is_seeded_document_example(exact) is True
    assert is_seeded_document_example(similar) is False


def test_document_services_remain_available_through_library_service_exports():
    assert library_services.DocumentService is DocumentService
    assert library_services.active_document_queryset is active_document_queryset
    assert library_services.document_action_capabilities is document_action_capabilities
