import pytest
from django.core.files.uploadedfile import SimpleUploadedFile

from apps.projects.models import ProjectMembership, ResearchProject
from tests.factories.accounts import UserFactory
from tests.helpers import authenticate


def _pdf(name="paper.pdf"):
    return SimpleUploadedFile(
        name, f"%PDF-1.4\n{name}\n%%EOF".encode(), content_type="application/pdf"
    )


@pytest.mark.django_db
def test_paper_upload_list_and_download_contract(api_client):
    teacher = UserFactory(global_role="advisor", status="active")
    student = UserFactory(global_role="student", status="active")
    project = ResearchProject.objects.create(title="Cloud Library", advisor=teacher)
    ProjectMembership.objects.create(project=project, user=teacher, role="advisor")
    ProjectMembership.objects.create(project=project, user=student, role="student")
    client = authenticate(api_client, student)

    upload_response = client.post(
        f"/api/projects/{project.id}/papers/",
        {
            "file": _pdf(),
            "title": "Searchable PDF Paper",
            "authors": "Ada Lovelace, Grace Hopper",
            "publicationYear": "2026",
            "keywords": "systems,collaboration",
        },
        format="multipart",
    )
    list_response = client.get(f"/api/projects/{project.id}/papers/?q=Grace")
    download_response = client.get(f"/api/papers/{upload_response.data['id']}/download")

    assert upload_response.status_code == 201
    assert upload_response.data["visibility"] == "project_members"
    assert upload_response.data["checksumSha256"]
    assert list_response.status_code == 200
    assert list_response.data["results"][0]["title"] == "Searchable PDF Paper"
    assert download_response.status_code == 200
    assert download_response.data["filename"] == "paper.pdf"


@pytest.mark.django_db
def test_paper_visibility_and_upload_validation_contract(api_client):
    teacher = UserFactory(global_role="advisor", status="active")
    student = UserFactory(global_role="student", status="active")
    outsider = UserFactory(global_role="student", status="active")
    project = ResearchProject.objects.create(title="Private Papers", advisor=teacher)
    ProjectMembership.objects.create(project=project, user=teacher, role="advisor")
    ProjectMembership.objects.create(project=project, user=student, role="student")

    student_client = authenticate(api_client, student)
    scoped_response = student_client.post(
        f"/api/projects/{project.id}/papers/",
        {"file": _pdf("scoped.pdf"), "title": "Scoped Paper", "authors": "Student"},
        format="multipart",
    )
    group_wide_response = authenticate(api_client, teacher).post(
        f"/api/projects/{project.id}/papers/",
        {
            "file": _pdf("group.pdf"),
            "title": "Group Wide Paper",
            "authors": "Teacher",
            "visibility": "group_wide",
        },
        format="multipart",
    )
    invalid_response = student_client.post(
        f"/api/projects/{project.id}/papers/",
        {
            "file": SimpleUploadedFile("paper.exe", b"bad", content_type="application/octet-stream"),
            "title": "Bad Paper",
            "authors": "Student",
        },
        format="multipart",
    )

    outsider_client = authenticate(api_client, outsider)
    visible_response = outsider_client.get(f"/api/projects/{project.id}/papers/?q=Paper")
    blocked_download = outsider_client.get(f"/api/papers/{scoped_response.data['id']}/download")

    assert scoped_response.status_code == 201
    assert group_wide_response.status_code == 201
    assert invalid_response.status_code == 400
    assert visible_response.status_code == 200
    assert [paper["title"] for paper in visible_response.data["results"]] == ["Group Wide Paper"]
    assert blocked_download.status_code == 403
