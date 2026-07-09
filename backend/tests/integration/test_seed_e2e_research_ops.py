import pytest
from django.core.files.storage import default_storage
from django.core.management import call_command

from apps.accounts.models import User
from apps.common.models import UploadedFile
from apps.library.models import DocumentCategory, DocumentRecord, PaperAttachment, PaperRecord
from apps.library.services.documents import (
    SEEDED_DOCUMENT_EXAMPLE_CHECKSUM_SHA256,
    SEEDED_DOCUMENT_EXAMPLE_ORIGINAL_FILENAME,
    SEEDED_DOCUMENT_EXAMPLE_STORED_NAME,
    SEEDED_DOCUMENT_EXAMPLE_TITLE,
)
from apps.notifications.models import Notification
from apps.operations.management.commands.seed_research_ops_e2e import Command
from apps.projects.models import ProjectMembership, ResearchProject
from apps.repositories.models import CodeArtifact, CodeArtifactVersion
from apps.resources.models import Booking, ResourceItem, ResourceType


@pytest.mark.django_db(transaction=True)
def test_seed_research_ops_e2e_creates_deterministic_full_stack_data():
    call_command("seed_research_ops_e2e", skip_migrate=True, verbosity=0)

    assert User.objects.filter(email="admin@gradsync.local", global_role="admin").exists()
    advisor = User.objects.get(email="advisor@example.edu")
    student = User.objects.get(email="student@example.edu")
    project = ResearchProject.objects.get(title="Graphene Lab")

    assert ProjectMembership.objects.filter(
        project=project, user=advisor, role="advisor", status="active"
    ).exists()
    assert ProjectMembership.objects.filter(
        project=project, user=student, role="student", status="active"
    ).exists()
    assert ResourceType.objects.filter(name="Microscope").exists()
    assert ResourceItem.objects.filter(name="Confocal microscope").exists()
    assert Booking.objects.filter(
        project=project, resource_item__name="Confocal microscope"
    ).exists()
    assert DocumentCategory.objects.filter(name="Protocols", status="active").exists()
    assert DocumentCategory.objects.filter(name="Reports", status="active").exists()
    assert Notification.objects.filter(project=project, recipient=advisor).exists()

    paper = PaperRecord.objects.get(project=project, title="Graph Neural Methods")
    attachment = PaperAttachment.objects.get(project=project, paper=paper)
    assert attachment.imported_by == advisor
    assert attachment.relative_path
    assert default_storage.exists(attachment.storage_key)

    artifact = CodeArtifact.objects.get(project=project, name="Analysis Toolkit")
    version = CodeArtifactVersion.objects.get(project=project, artifact=artifact)
    assert version.imported_by == advisor
    assert version.relative_path_manifest
    assert default_storage.exists(version.storage_key)
    assert not CodeArtifact.objects.filter(
        project=project,
        name="Simulator",
        source_path_label="team-library/code/simulator",
    ).exists()
    assert not DocumentRecord.objects.filter(
        project=project,
        title=SEEDED_DOCUMENT_EXAMPLE_TITLE,
        category__name="Protocols",
        document_file__stored_name=SEEDED_DOCUMENT_EXAMPLE_STORED_NAME,
        checksum_sha256=SEEDED_DOCUMENT_EXAMPLE_CHECKSUM_SHA256,
    ).exists()


@pytest.mark.django_db(transaction=True)
def test_seed_research_ops_e2e_can_run_twice_without_stale_field_errors():
    call_command("seed_research_ops_e2e", skip_migrate=True, verbosity=0)
    call_command("seed_research_ops_e2e", skip_migrate=True, verbosity=0)

    assert User.objects.count() == 3
    assert ResearchProject.objects.count() == 1
    assert ResourceType.objects.filter(name="Microscope").count() == 1
    assert DocumentCategory.objects.filter(status="active").count() == 2


@pytest.mark.django_db(transaction=True)
def test_seed_research_ops_validation_does_not_reintroduce_seeded_code_samples():
    call_command("seed_research_ops_validation", verbosity=0)

    assert not CodeArtifact.objects.filter(
        name="Materials simulator",
        source_path_label="team-code/materials-simulator",
        versions__storage_key="validation/code/materials-simulator.zip",
        versions__filename="materials-simulator.zip",
        versions__checksum_sha256="e" * 64,
    ).exists()
    assert not DocumentRecord.objects.filter(
        title=SEEDED_DOCUMENT_EXAMPLE_TITLE,
        document_file__stored_name=SEEDED_DOCUMENT_EXAMPLE_STORED_NAME,
        checksum_sha256=SEEDED_DOCUMENT_EXAMPLE_CHECKSUM_SHA256,
    ).exists()
    assert DocumentCategory.objects.filter(name="Protocols", status="active").exists()
    assert DocumentCategory.objects.filter(name="Reports", status="active").exists()


@pytest.mark.django_db(transaction=True)
def test_cleanup_seeded_code_artifacts_is_exact_and_repeatable():
    call_command("seed_research_ops_e2e", skip_migrate=True, verbosity=0)
    advisor = User.objects.get(email="advisor@example.edu")
    project = ResearchProject.objects.get(title="Graphene Lab")
    seeded = CodeArtifact.objects.create(
        project=project,
        name="Simulator",
        source_path_label="team-library/code/simulator",
        created_by=advisor,
    )
    CodeArtifactVersion.objects.create(
        artifact=seeded,
        project=project,
        version_label="v1",
        storage_key="e2e/sim.zip",
        filename="sim.zip",
        checksum_sha256="b" * 64,
        imported_by=advisor,
    )
    preserved = CodeArtifact.objects.create(
        project=project,
        name="Simulator",
        source_path_label="user-uploads/simulator",
        created_by=advisor,
    )
    CodeArtifactVersion.objects.create(
        artifact=preserved,
        project=project,
        version_label="v1",
        storage_key="user/sim.zip",
        filename="sim.zip",
        checksum_sha256="b" * 64,
        imported_by=advisor,
    )

    call_command("cleanup_seeded_code_artifacts", verbosity=0)
    call_command("cleanup_seeded_code_artifacts", verbosity=0)

    assert not CodeArtifact.objects.filter(pk=seeded.pk).exists()
    assert CodeArtifact.objects.filter(pk=preserved.pk).exists()
    visible_names = list(
        CodeArtifact.objects.filter(project=project, status=CodeArtifact.Status.ACTIVE)
        .order_by("name")
        .values_list("name", flat=True)
    )
    assert visible_names == ["Analysis Toolkit", "Simulator"]


@pytest.mark.django_db(transaction=True)
def test_cleanup_seeded_library_documents_is_exact_and_repeatable():
    call_command("seed_research_ops_e2e", skip_migrate=True, verbosity=0)
    advisor = User.objects.get(email="advisor@example.edu")
    project = ResearchProject.objects.get(title="Graphene Lab")
    category = DocumentCategory.objects.get(name="Protocols")
    seeded_file = UploadedFile.objects.create(
        owner=advisor,
        category=UploadedFile.Category.DOCUMENT,
        original_filename=SEEDED_DOCUMENT_EXAMPLE_ORIGINAL_FILENAME,
        stored_name=SEEDED_DOCUMENT_EXAMPLE_STORED_NAME,
        content_type="application/pdf",
        size_bytes=128,
        checksum_sha256=SEEDED_DOCUMENT_EXAMPLE_CHECKSUM_SHA256,
    )
    seeded = DocumentRecord.objects.create(
        project=project,
        category=category,
        title=SEEDED_DOCUMENT_EXAMPLE_TITLE,
        document_file=seeded_file,
        checksum_sha256=SEEDED_DOCUMENT_EXAMPLE_CHECKSUM_SHA256,
        created_by=advisor,
    )
    preserved_file = UploadedFile.objects.create(
        owner=advisor,
        category=UploadedFile.Category.DOCUMENT,
        original_filename=SEEDED_DOCUMENT_EXAMPLE_ORIGINAL_FILENAME,
        stored_name="user/example-protocol.pdf",
        content_type="application/pdf",
        size_bytes=128,
        checksum_sha256=SEEDED_DOCUMENT_EXAMPLE_CHECKSUM_SHA256,
    )
    preserved = DocumentRecord.objects.create(
        project=project,
        category=category,
        title=SEEDED_DOCUMENT_EXAMPLE_TITLE,
        document_file=preserved_file,
        checksum_sha256=SEEDED_DOCUMENT_EXAMPLE_CHECKSUM_SHA256,
        created_by=advisor,
    )

    call_command("cleanup_seeded_library_documents", verbosity=0)
    call_command("cleanup_seeded_library_documents", verbosity=0)

    assert not DocumentRecord.objects.filter(pk=seeded.pk).exists()
    assert not UploadedFile.objects.filter(pk=seeded_file.pk).exists()
    assert DocumentRecord.objects.filter(pk=preserved.pk).exists()
    assert UploadedFile.objects.filter(pk=preserved_file.pk).exists()


def test_seed_research_ops_e2e_runs_migrations_before_flushing_by_default(monkeypatch):
    command = Command()
    call_order = []

    def fake_call_command(name, *args, **kwargs):
        call_order.append(name)

    monkeypatch.setattr(
        "apps.operations.management.commands.seed_research_ops_e2e.call_command",
        fake_call_command,
    )
    monkeypatch.setattr(
        "apps.operations.management.commands.seed_research_ops_e2e.get_user_model",
        lambda: (_ for _ in ()).throw(AssertionError("stop after migration preflight")),
    )

    with pytest.raises(AssertionError, match="stop after migration preflight"):
        command.handle(skip_migrate=False, verbosity=0)

    assert call_order[:2] == ["migrate", "flush"]
