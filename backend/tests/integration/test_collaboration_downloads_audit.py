import pytest

from apps.audit.models import AuditEvent, DownloadEvent
from apps.common.downloads import describe_uploaded_file_download
from apps.library.services.downloads import describe_document_download, describe_paper_download
from apps.projects.models import ProjectMembership, ResearchProject
from apps.repositories.download_services import describe_code_artifact_download
from tests.factories.accounts import UserFactory
from tests.factories.collaboration import (
    UploadedFileFactory,
    active_code_artifact,
    active_project_document,
    active_shared_pdf_paper,
)


@pytest.mark.django_db
def test_download_helper_requires_visibility_and_records_audit_event():
    teacher = UserFactory(global_role="advisor", status="active")
    student = UserFactory(global_role="student", status="active")
    project = ResearchProject.objects.create(title="P1", advisor=teacher)
    ProjectMembership.objects.create(project=project, user=student, role="student")
    uploaded = UploadedFileFactory(owner=teacher)

    descriptor = describe_uploaded_file_download(
        student,
        uploaded,
        project=project,
        visibility="project_members",
        asset_type="paper",
    )

    assert descriptor["filename"] == uploaded.original_filename
    assert DownloadEvent.objects.filter(actor=student, target_id=str(uploaded.id)).exists()
    assert AuditEvent.objects.filter(actor=student, event_type="paper.downloaded").exists()


@pytest.mark.django_db
def test_download_helper_blocks_non_member_for_project_scoped_file():
    teacher = UserFactory(global_role="advisor", status="active")
    outsider = UserFactory(global_role="student", status="active")
    project = ResearchProject.objects.create(title="P1", advisor=teacher)
    uploaded = UploadedFileFactory(owner=teacher)

    with pytest.raises(PermissionError):
        describe_uploaded_file_download(
            outsider,
            uploaded,
            project=project,
            visibility="project_members",
            asset_type="paper",
        )


@pytest.mark.django_db
def test_domain_download_services_record_equivalent_audit_events():
    teacher = UserFactory(global_role="advisor", status="active")
    student = UserFactory(global_role="student", status="active")
    project = ResearchProject.objects.create(title="Domain Downloads", advisor=teacher)
    ProjectMembership.objects.create(project=project, user=student, role="student")
    paper = active_shared_pdf_paper(
        project=project,
        created_by=teacher,
        visibility="project_members",
    )
    document = active_project_document(project=project, created_by=teacher)
    code_artifact = active_code_artifact(project=project, created_by=teacher)

    paper_descriptor = describe_paper_download(student, paper)
    document_descriptor = describe_document_download(student, document)
    code_descriptor = describe_code_artifact_download(student, code_artifact)

    assert paper_descriptor["deliveryMode"] == "direct_response"
    assert document_descriptor["deliveryMode"] == "direct_response"
    assert code_descriptor["deliveryMode"] == "direct_response"
    assert AuditEvent.objects.filter(actor=student, event_type="paper.downloaded").exists()
    assert AuditEvent.objects.filter(actor=student, event_type="document.downloaded").exists()
    assert AuditEvent.objects.filter(
        actor=student,
        event_type="code_artifact_version.downloaded",
    ).exists()
    assert DownloadEvent.objects.filter(actor=student).count() == 3
