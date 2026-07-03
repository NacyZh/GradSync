import pytest
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

    artifact = CodeArtifact.objects.get(project=project, name="Simulator")
    version = CodeArtifactVersion.objects.get(project=project, artifact=artifact)
    assert version.imported_by == advisor
    assert version.relative_path_manifest


@pytest.mark.django_db(transaction=True)
def test_seed_e2e_research_ops_can_run_twice_without_stale_field_errors():
    call_command("seed_e2e_research_ops", skip_migrate=True, verbosity=0)
    call_command("seed_e2e_research_ops", skip_migrate=True, verbosity=0)

    assert User.objects.count() == 3
    assert ResearchProject.objects.count() == 1
    assert ResourceType.objects.filter(name="Microscope").count() == 1


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
