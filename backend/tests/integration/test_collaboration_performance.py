import time

import pytest
from django.utils import timezone

from apps.library.models import DocumentCategory, DocumentRecord
from apps.notifications.models import Notification
from apps.projects.models import ProjectMembership, ResearchProject
from apps.resources.models import ResourceItem, ResourceType, ResourceUseSubmission
from apps.submissions.models import WritingProject, WritingVersion
from tests.factories.accounts import UserFactory
from tests.factories.collaboration import UploadedFileFactory
from tests.helpers import authenticate


@pytest.mark.django_db
def test_cross_story_lists_return_within_release_thresholds(api_client):
    advisor = UserFactory(global_role="advisor", status="active")
    student = UserFactory(global_role="student", status="active")
    project = ResearchProject.objects.create(title="Collaboration Performance", advisor=advisor)
    ProjectMembership.objects.create(project=project, user=advisor, role="advisor")
    ProjectMembership.objects.create(project=project, user=student, role="student")
    category = DocumentCategory.objects.create(name="Protocols", created_by=advisor)
    doc_file = UploadedFileFactory(
        owner=advisor, category="document", original_filename="protocol.pdf"
    )
    writing_file = UploadedFileFactory(
        owner=student, category="writing", original_filename="draft.docx"
    )
    resource_type = ResourceType.objects.create(name="Instrument")
    resource = ResourceItem.objects.create(resource_type=resource_type, name="Spectrometer")

    DocumentRecord.objects.bulk_create(
        [
            DocumentRecord(
                project=project,
                category=category,
                title=f"Protocol {index}",
                description="Calibration workflow",
                document_file=doc_file,
                checksum_sha256=f"{index:064x}"[-64:],
                created_by=advisor,
            )
            for index in range(250)
        ]
    )
    writing_projects = WritingProject.objects.bulk_create(
        [
            WritingProject(
                project=project,
                student=student,
                title=f"Thesis Chapter {index}",
                writing_type=WritingProject.WritingType.THESIS,
            )
            for index in range(60)
        ]
    )
    WritingVersion.objects.bulk_create(
        [
            WritingVersion(
                writing_project=writing_project,
                version_number=1,
                submitted_by=student,
                draft_file=writing_file,
                file_kind=WritingVersion.FileKind.WORD,
            )
            for writing_project in writing_projects
        ]
    )
    ResourceUseSubmission.objects.bulk_create(
        [
            ResourceUseSubmission(
                resource_item=resource,
                student=student,
                submission_type=ResourceUseSubmission.SubmissionType.REQUEST,
                details=f"Use request {index}",
            )
            for index in range(120)
        ]
    )
    Notification.objects.bulk_create(
        [
            Notification(
                project=project,
                recipient=student,
                recipient_email=student.email,
                sender=advisor,
                event_type=Notification.EventType.TEACHER_FEEDBACK_AVAILABLE,
                target_type="TeacherFeedback",
                target_id=str(index),
                subject=f"Feedback available {index}",
                status=Notification.Status.PENDING,
                eligible_at=timezone.now(),
            )
            for index in range(120)
        ]
    )

    client = authenticate(api_client, student)
    start = time.monotonic()
    responses = [
        client.get(f"/api/projects/{project.id}/documents?q=Protocol&page_size=50"),
        client.get(f"/api/projects/{project.id}/writing-projects/?q=Thesis&page_size=50"),
        client.get("/api/resources/?search=Spectrometer&page_size=50"),
        client.get(f"/api/projects/{project.id}/notifications/"),
    ]
    elapsed = time.monotonic() - start

    assert all(response.status_code == 200 for response in responses)
    assert len(responses[0].data["results"]) == 50
    assert len(responses[1].data["results"]) == 50
    assert elapsed < 2


@pytest.mark.django_db
def test_upload_feedback_and_permitted_download_paths_are_fast(api_client):
    advisor = UserFactory(global_role="advisor", status="active")
    student = UserFactory(global_role="student", status="active")
    project = ResearchProject.objects.create(title="Download Performance", advisor=advisor)
    ProjectMembership.objects.create(project=project, user=advisor, role="advisor")
    ProjectMembership.objects.create(project=project, user=student, role="student")
    category = DocumentCategory.objects.create(name="Reports", created_by=advisor)
    doc_file = UploadedFileFactory(
        owner=advisor, category="document", original_filename="report.pdf"
    )
    document = DocumentRecord.objects.create(
        project=project,
        category=category,
        title="Performance Report",
        description="Download validation",
        document_file=doc_file,
        checksum_sha256=doc_file.checksum_sha256,
        created_by=advisor,
    )

    client = authenticate(api_client, student)
    start = time.monotonic()
    response = client.get(f"/api/documents/{document.id}/download")
    elapsed = time.monotonic() - start

    assert response.status_code == 200
    assert response.data["filename"] == "report.pdf"
    assert elapsed < 5
