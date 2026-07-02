import pytest

from apps.library.duplicate_services import (
    find_duplicate,
    normalize_doi,
    title_author_year_fingerprint,
)
from apps.library.models import PaperAttachment, PaperRecord
from apps.projects.models import ProjectMembership, ResearchProject
from tests.factories.accounts import UserFactory


@pytest.mark.django_db
def test_paper_duplicate_precedence_checksum_then_doi_then_title_author_year():
    user = UserFactory()
    project = ResearchProject.objects.create(title="Project", advisor=user)
    ProjectMembership.objects.create(project=project, user=user, role="student")
    checksum_paper = PaperRecord.objects.create(
        project=project,
        title="Checksum Paper",
        authors=["A"],
        publication_year=2025,
        doi="10.1/checksum",
        fingerprint=title_author_year_fingerprint(
            title="Checksum Paper", authors=["A"], publication_year=2025
        ),
        created_by=user,
    )
    PaperAttachment.objects.create(
        paper=checksum_paper,
        project=project,
        storage_key="p.pdf",
        filename="p.pdf",
        checksum_sha256="d" * 64,
        uploaded_by=user,
    )
    doi_paper = PaperRecord.objects.create(
        project=project,
        title="DOI Paper",
        authors=["B"],
        publication_year=2026,
        doi="10.1/doi",
        fingerprint=title_author_year_fingerprint(
            title="DOI Paper", authors=["B"], publication_year=2026
        ),
        created_by=user,
    )

    match = find_duplicate(
        project,
        checksum_sha256="d" * 64,
        doi="10.1/doi",
        title="DOI Paper",
        authors=["B"],
        publication_year=2026,
    )
    assert match.paper == checksum_paper
    assert match.reason == "checksum"

    match = find_duplicate(project, doi="https://doi.org/10.1/doi")
    assert match.paper == doi_paper
    assert match.reason == "doi"

    match = find_duplicate(project, title="DOI Paper", authors=["B"], publication_year=2026)
    assert match.paper == doi_paper
    assert match.reason == "title_author_year"


def test_doi_and_fingerprint_normalization():
    assert normalize_doi("https://doi.org/10.1000/ABC") == "10.1000/abc"
    assert (
        title_author_year_fingerprint(
            title=" Graph: Neural Methods! ", authors=["Lin, Chen"], publication_year=2026
        )
        == "graph neural methods|lin chen|2026"
    )
