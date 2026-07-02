import pytest

from apps.library.models import PaperAttachment, PaperRecord
from apps.projects.models import ProjectMembership, ResearchProject
from tests.factories.accounts import UserFactory
from tests.helpers import authenticate


@pytest.mark.django_db
def test_paper_create_import_duplicate_and_authorized_download(api_client):
    advisor = UserFactory(global_role="advisor")
    student = UserFactory(global_role="student")
    outsider = UserFactory(global_role="student")
    project = ResearchProject.objects.create(title="AI Lab", advisor=advisor)
    ProjectMembership.objects.create(project=project, user=advisor, role="advisor")
    ProjectMembership.objects.create(project=project, user=student, role="student")

    client = authenticate(api_client, student)
    create_response = client.post(
        f"/api/projects/{project.id}/papers/",
        {
            "title": "Graph Neural Methods",
            "authors": ["Lin Chen", "Ada Yu"],
            "venue": "GradSync Conf",
            "publicationYear": 2026,
            "doi": "https://doi.org/10.1000/gradsync",
            "tags": ["gnn"],
        },
        format="json",
    )

    assert create_response.status_code == 201
    paper = PaperRecord.objects.get(pk=create_response.data["id"])
    PaperAttachment.objects.create(
        paper=paper,
        project=project,
        storage_key="papers/graph.pdf",
        filename="graph.pdf",
        content_type="application/pdf",
        size_bytes=1024,
        checksum_sha256="a" * 64,
        uploaded_by=student,
    )

    duplicate_response = client.post(
        f"/api/projects/{project.id}/papers/",
        {
            "title": "Graph Neural Methods",
            "authors": ["Lin Chen"],
            "publicationYear": 2026,
            "doi": "10.1000/gradsync",
        },
        format="json",
    )
    assert duplicate_response.status_code == 409
    assert duplicate_response.data["duplicateReason"] == "doi"

    import_response = client.post(
        f"/api/projects/{project.id}/papers/imports/",
        {
            "sourceType": "mixed",
            "items": [
                {"title": "New Paper", "authors": ["Mei Wang"], "publicationYear": 2025},
                {"title": "Graph Neural Methods", "authors": ["Lin Chen"], "publicationYear": 2026},
            ],
        },
        format="json",
    )
    assert import_response.status_code == 201
    assert import_response.data["acceptedCount"] == 1
    assert import_response.data["duplicateCount"] == 1
    assert import_response.data["results"][1]["duplicateReason"] == "title_author_year"

    download_response = client.post(f"/api/projects/{project.id}/papers/{paper.id}/download/")
    assert download_response.status_code == 200
    assert download_response.data["filename"] == "graph.pdf"

    outsider_response = authenticate(api_client, outsider).post(
        f"/api/projects/{project.id}/papers/{paper.id}/download/"
    )
    assert outsider_response.status_code == 404


@pytest.mark.django_db
def test_paper_upload_rejection_is_enforced_by_policy():
    from django.core.exceptions import ValidationError

    from apps.library.upload_policy import validate_paper_upload

    with pytest.raises(ValidationError):
        validate_paper_upload(
            filename="too-large.pdf",
            content_type="application/pdf",
            size_bytes=51 * 1024 * 1024,
        )

    with pytest.raises(ValidationError):
        validate_paper_upload(filename="paper.exe", content_type="application/octet-stream")
