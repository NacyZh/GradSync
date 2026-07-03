import pytest
from django.core.files.uploadedfile import SimpleUploadedFile

from apps.audit.models import AuditEvent, DownloadEvent
from apps.library.models import PaperRecord
from apps.projects.models import ProjectMembership, ResearchProject
from tests.factories.accounts import UserFactory
from tests.helpers import authenticate


def _pdf(name: str, body: bytes = b"%PDF-1.4\npaper\n%%EOF"):
    return SimpleUploadedFile(name, body, content_type="application/pdf")


@pytest.mark.django_db
def test_pdf_upload_search_visibility_and_download_audit(api_client):
    teacher = UserFactory(global_role="advisor", status="active")
    student = UserFactory(global_role="student", status="active")
    outsider = UserFactory(global_role="student", status="active")
    project = ResearchProject.objects.create(title="Paper Project", advisor=teacher)
    ProjectMembership.objects.create(project=project, user=teacher, role="advisor")
    ProjectMembership.objects.create(project=project, user=student, role="student")
    client = authenticate(api_client, student)

    response = client.post(
        f"/api/projects/{project.id}/papers/",
        {
            "file": _pdf("graph.pdf"),
            "title": "Graph Neural Collaboration",
            "authors": "Lin Chen, Mei Wang",
            "venue": "GradSync Conf",
            "publicationYear": "2026",
            "keywords": "graph,collaboration",
            "abstract": "Project-scoped graph research.",
        },
        format="multipart",
    )
    assert response.status_code == 201

    paper = PaperRecord.objects.get(pk=response.data["id"])
    assert paper.uploaded_file is not None
    assert paper.visibility == "project_members"
    assert paper.checksum_sha256 == paper.uploaded_file.checksum_sha256

    search_response = client.get(f"/api/projects/{project.id}/papers/?q=Mei")
    assert search_response.status_code == 200
    assert [item["title"] for item in search_response.data["results"]] == [
        "Graph Neural Collaboration"
    ]

    download_response = client.get(f"/api/papers/{paper.id}/download")
    assert download_response.status_code == 200
    assert DownloadEvent.objects.filter(actor=student, target_id=str(paper.uploaded_file_id)).exists()
    assert AuditEvent.objects.filter(actor=student, event_type="paper.downloaded").exists()

    outsider_client = authenticate(api_client, outsider)
    hidden_response = outsider_client.get(f"/api/projects/{project.id}/papers/?q=Graph")
    assert hidden_response.status_code == 200
    assert hidden_response.data["results"] == []


@pytest.mark.django_db
def test_group_wide_paper_is_visible_to_non_member_and_student_cannot_set_group_wide(api_client):
    teacher = UserFactory(global_role="advisor", status="active")
    student = UserFactory(global_role="student", status="active")
    outsider = UserFactory(global_role="student", status="active")
    project = ResearchProject.objects.create(title="Shared Project", advisor=teacher)
    ProjectMembership.objects.create(project=project, user=teacher, role="advisor")
    ProjectMembership.objects.create(project=project, user=student, role="student")

    student_response = authenticate(api_client, student).post(
        f"/api/projects/{project.id}/papers/",
        {
            "file": _pdf("student.pdf"),
            "title": "Student Shared Attempt",
            "authors": "Student",
            "visibility": "group_wide",
        },
        format="multipart",
    )
    teacher_response = authenticate(api_client, teacher).post(
        f"/api/projects/{project.id}/papers/",
        {
            "file": _pdf("teacher.pdf"),
            "title": "Teacher Shared Paper",
            "authors": "Teacher",
            "visibility": "group_wide",
        },
        format="multipart",
    )
    outsider_response = authenticate(api_client, outsider).get(
        f"/api/projects/{project.id}/papers/?q=Teacher"
    )

    assert student_response.status_code == 403
    assert teacher_response.status_code == 201
    assert outsider_response.status_code == 200
    assert outsider_response.data["results"][0]["visibility"] == "group_wide"


@pytest.mark.django_db
def test_invalid_uploads_and_duplicates_are_rejected(api_client):
    teacher = UserFactory(global_role="advisor", status="active")
    project = ResearchProject.objects.create(title="Validation Project", advisor=teacher)
    ProjectMembership.objects.create(project=project, user=teacher, role="advisor")
    client = authenticate(api_client, teacher)

    first = client.post(
        f"/api/projects/{project.id}/papers/",
        {"file": _pdf("duplicate.pdf", b"%PDF-1.4\nsame\n%%EOF"), "title": "Duplicate", "authors": "A"},
        format="multipart",
    )
    duplicate = client.post(
        f"/api/projects/{project.id}/papers/",
        {"file": _pdf("duplicate-again.pdf", b"%PDF-1.4\nsame\n%%EOF"), "title": "Duplicate Again", "authors": "A"},
        format="multipart",
    )
    invalid = client.post(
        f"/api/projects/{project.id}/papers/",
        {"file": SimpleUploadedFile("bad.txt", b"not pdf", content_type="text/plain"), "title": "Bad", "authors": "A"},
        format="multipart",
    )

    assert first.status_code == 201
    assert duplicate.status_code == 409
    assert duplicate.data["duplicateReason"] == "checksum"
    assert invalid.status_code == 400
