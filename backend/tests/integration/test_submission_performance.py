import pytest

from apps.common.models import UploadedFile
from apps.projects.models import ProjectMembership, ResearchProject
from apps.submissions.models import Draft, WritingProject, WritingVersion
from tests.factories.accounts import UserFactory
from tests.helpers import authenticate


@pytest.mark.django_db
def test_draft_list_handles_project_scoped_records(api_client):
    advisor = UserFactory(global_role="advisor")
    student = UserFactory(global_role="student")
    project = ResearchProject.objects.create(title="Performance", advisor=advisor)
    ProjectMembership.objects.create(project=project, user=student, role="student")
    Draft.objects.bulk_create(
        [Draft(project=project, student=student, title=f"Draft {index}") for index in range(200)]
    )

    response = authenticate(api_client, student).get(f"/api/projects/{project.id}/drafts/")

    assert response.status_code == 200
    assert len(response.json()["results"]) == 50


@pytest.mark.django_db
def test_writing_project_list_paginates_versions_and_feedback_status(api_client):
    advisor = UserFactory(global_role="advisor")
    student = UserFactory(global_role="student")
    project = ResearchProject.objects.create(title="Writing Performance", advisor=advisor)
    ProjectMembership.objects.create(project=project, user=advisor, role="advisor")
    ProjectMembership.objects.create(project=project, user=student, role="student")
    writing_projects = [
        WritingProject(
            project=project,
            student=student,
            title=f"Writing Project {index:03d}",
            writing_type=WritingProject.WritingType.PAPER,
        )
        for index in range(120)
    ]
    WritingProject.objects.bulk_create(writing_projects)
    uploads = [
        UploadedFile(
            owner=student,
            category=UploadedFile.Category.WRITING,
            original_filename=f"draft-{index}.docx",
            stored_name=f"collaboration/writing/draft-{index}.docx",
            size_bytes=128,
            checksum_sha256=f"{index:064x}"[-64:],
        )
        for index in range(120)
    ]
    UploadedFile.objects.bulk_create(uploads)
    versions = [
        WritingVersion(
            writing_project=writing_project,
            version_number=1,
            submitted_by=student,
            draft_file=upload,
            file_kind=WritingVersion.FileKind.WORD,
        )
        for writing_project, upload in zip(writing_projects, uploads, strict=True)
    ]
    WritingVersion.objects.bulk_create(versions)

    response = authenticate(api_client, student).get(
        f"/api/projects/{project.id}/writing-projects/?q=Writing"
    )

    assert response.status_code == 200
    assert len(response.json()["results"]) == 50
    assert response.json()["results"][0]["versions"][0]["status"] == "submitted"
