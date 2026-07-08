import pytest
from django.core.files.storage import default_storage
from django.core.management import call_command

from apps.accounts.management.commands.seed_e2e_research_ops import Command
from apps.accounts.models import User
from apps.library.models import PaperAttachment, PaperRecord
from apps.notifications.models import Notification
from apps.projects.models import ProjectMembership, ResearchProject
from apps.repositories.models import CodeArtifact, CodeArtifactVersion
from apps.resources.models import Booking, ResourceItem, ResourceType


@pytest.mark.django_db(transaction=True)
def test_seed_e2e_research_ops_creates_deterministic_full_stack_data():
    call_command("seed_e2e_research_ops", skip_migrate=True, verbosity=0)

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


@pytest.mark.django_db(transaction=True)
def test_seed_e2e_research_ops_can_run_twice_without_stale_field_errors():
    call_command("seed_e2e_research_ops", skip_migrate=True, verbosity=0)
    call_command("seed_e2e_research_ops", skip_migrate=True, verbosity=0)

    assert User.objects.count() == 3
    assert ResearchProject.objects.count() == 1
    assert ResourceType.objects.filter(name="Microscope").count() == 1


@pytest.mark.django_db(transaction=True)
def test_seed_validation_research_ops_does_not_reintroduce_seeded_code_samples():
    call_command("seed_validation_research_ops", verbosity=0)

    assert not CodeArtifact.objects.filter(
        name="Materials simulator",
        source_path_label="team-code/materials-simulator",
        versions__storage_key="validation/code/materials-simulator.zip",
        versions__filename="materials-simulator.zip",
        versions__checksum_sha256="e" * 64,
    ).exists()


@pytest.mark.django_db(transaction=True)
def test_remove_seeded_code_samples_is_exact_and_repeatable():
    call_command("seed_e2e_research_ops", skip_migrate=True, verbosity=0)
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

    call_command("remove_seeded_code_samples", verbosity=0)
    call_command("remove_seeded_code_samples", verbosity=0)

    assert not CodeArtifact.objects.filter(pk=seeded.pk).exists()
    assert CodeArtifact.objects.filter(pk=preserved.pk).exists()
    visible_names = list(
        CodeArtifact.objects.filter(project=project, status=CodeArtifact.Status.ACTIVE)
        .order_by("name")
        .values_list("name", flat=True)
    )
    assert visible_names == ["Analysis Toolkit", "Simulator"]


def test_seed_e2e_research_ops_runs_migrations_before_flushing_by_default(monkeypatch):
    command = Command()
    call_order = []

    def fake_call_command(name, *args, **kwargs):
        call_order.append(name)

    monkeypatch.setattr(
        "apps.accounts.management.commands.seed_e2e_research_ops.call_command",
        fake_call_command,
    )
    monkeypatch.setattr(
        "apps.accounts.management.commands.seed_e2e_research_ops.get_user_model",
        lambda: (_ for _ in ()).throw(AssertionError("stop after migration preflight")),
    )

    with pytest.raises(AssertionError, match="stop after migration preflight"):
        command.handle(skip_migrate=False, verbosity=0)

    assert call_order[:2] == ["migrate", "flush"]
