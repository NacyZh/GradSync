import pytest

from apps.audit.models import AuditEvent, DownloadEvent
from apps.common.downloads import describe_uploaded_file_download
from apps.projects.models import ProjectMembership, ResearchProject
from tests.factories.accounts import UserFactory
from tests.factories.collaboration import UploadedFileFactory


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
