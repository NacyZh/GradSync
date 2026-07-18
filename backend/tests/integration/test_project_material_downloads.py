import pytest
from django.core.files.base import ContentFile
from django.core.files.storage import default_storage

from apps.audit.models import AuditEvent, DownloadEvent
from apps.projects.models import ProjectMaterial
from tests.factories.collaboration import CodeArtifactVersionFactory, PaperRecordFactory
from tests.factories.shared_workspace import (
    active_student,
    active_teacher,
    group_wide_project_code,
    project_only_document,
    project_with_members,
)
from tests.helpers import authenticate


def _material(project, record, material_type):
    return ProjectMaterial.objects.create(
        source_project=project,
        material_type=material_type,
        backing_record_id=record.id,
        visibility_state=ProjectMaterial.VisibilityState.PROJECT_ONLY,
        classification_state=ProjectMaterial.ClassificationState.ACTIVE,
        classification_reason=ProjectMaterial.ClassificationReason.EXPLICIT_PROJECT_SPECIFIC,
        created_by=project.advisor,
    )


def _put_file(storage_key: str, content: bytes = b"project material"):
    if default_storage.exists(storage_key):
        default_storage.delete(storage_key)
    default_storage.save(storage_key, ContentFile(content))


@pytest.mark.django_db
def test_project_material_downloads_document_paper_and_code_with_audit(api_client):
    advisor = active_teacher()
    student = active_student()
    project = project_with_members(advisor=advisor, students=[student])
    document = project_only_document(project)
    paper = PaperRecordFactory(
        project=project,
        source_project=project,
        visibility="project_members",
    )
    code = group_wide_project_code(project, visibility="project_members")
    code_version = CodeArtifactVersionFactory(artifact=code, project=project)
    _put_file(document.document_file.stored_name)
    _put_file(paper.uploaded_file.stored_name)
    _put_file(code_version.storage_key)
    materials = [
        _material(project, document, ProjectMaterial.MaterialType.DOCUMENT),
        _material(project, paper, ProjectMaterial.MaterialType.PAPER),
        _material(project, code, ProjectMaterial.MaterialType.CODE),
    ]
    client = authenticate(api_client, student)

    for material in materials:
        response = client.post(f"/api/projects/{project.id}/materials/{material.id}/download/")
        assert response.status_code == 200
        assert response.headers["Content-Disposition"].startswith("attachment;")

    assert DownloadEvent.objects.filter(project=project, actor=student).count() == 3
    assert (
        AuditEvent.objects.filter(
            project=project,
            actor=student,
            event_type__contains="download",
        ).count()
        == 3
    )


@pytest.mark.django_db
def test_project_material_download_unavailable_exposes_no_file(api_client):
    advisor = active_teacher()
    student = active_student()
    project = project_with_members(advisor=advisor, students=[student])
    material = ProjectMaterial.objects.create(
        source_project=project,
        material_type=ProjectMaterial.MaterialType.DOCUMENT,
        backing_record_id=999999,
        visibility_state=ProjectMaterial.VisibilityState.PROJECT_ONLY,
        classification_state=ProjectMaterial.ClassificationState.ACTIVE,
        classification_reason=ProjectMaterial.ClassificationReason.EXPLICIT_PROJECT_SPECIFIC,
        created_by=advisor,
    )

    response = authenticate(api_client, student).post(
        f"/api/projects/{project.id}/materials/{material.id}/download/"
    )

    assert response.status_code == 410
    assert DownloadEvent.objects.filter(project=project, actor=student).count() == 0
