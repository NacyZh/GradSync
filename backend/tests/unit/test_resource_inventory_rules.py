import pytest
from django.core.exceptions import ValidationError
from django.utils import timezone

from apps.audit.models import AuditEvent
from apps.projects.models import ResearchProject
from apps.resources.models import Booking, ResourceItem, ResourceType, ResourceUseSubmission
from apps.resources.services import ResourceInventoryService
from tests.factories.accounts import UserFactory


@pytest.mark.django_db
def test_quantity_policy_and_optimistic_version_rules():
    manager = UserFactory(global_role="advisor", status="active")
    resource_type = ResourceType.objects.create(
        name="Instrument", confirmation_policy=ResourceType.ConfirmationPolicy.APPROVAL_REQUIRED
    )
    resource = ResourceItem.objects.create(
        resource_type=resource_type, name="Microscope", total_quantity=3, manager=manager
    )
    assert resource.effective_confirmation_policy == "approval_required"
    resource.confirmation_policy_override = ResourceType.ConfirmationPolicy.IMMEDIATE
    assert resource.effective_confirmation_policy == "immediate"

    service = ResourceInventoryService(manager)
    with pytest.raises(ValidationError):
        service.update_resource(resource, version=99, total_quantity=2)
    updated = service.update_resource(resource, version=1, total_quantity=2)
    assert updated.total_quantity == 2
    assert updated.version == 2


@pytest.mark.django_db
def test_safe_minimum_and_delete_eligibility_preserve_audit_snapshot():
    manager = UserFactory(global_role="advisor", status="active")
    student = UserFactory(global_role="student", status="active")
    project = ResearchProject.objects.create(title="Legacy", advisor=manager)
    resource_type = ResourceType.objects.create(name="Seat")
    dependent = ResourceItem.objects.create(
        resource_type=resource_type, name="Dependent", total_quantity=2, manager=manager
    )
    starts = timezone.now() + timezone.timedelta(days=1)
    Booking.objects.create(
        project=project,
        resource_item=dependent,
        requested_by=student,
        starts_at=starts,
        ends_at=starts + timezone.timedelta(hours=1),
    )
    Booking.objects.create(
        project=project,
        resource_item=dependent,
        requested_by=student,
        starts_at=starts + timezone.timedelta(minutes=15),
        ends_at=starts + timezone.timedelta(minutes=45),
    )
    with pytest.raises(ValidationError):
        ResourceInventoryService(manager).update_resource(
            dependent, version=1, total_quantity=1
        )
    with pytest.raises(ValidationError):
        ResourceInventoryService(manager).delete_resource(dependent)

    deletable = ResourceItem.objects.create(
        resource_type=resource_type, name="Deletable", total_quantity=1, manager=manager
    )
    resource_id = deletable.pk
    ResourceInventoryService(manager).delete_resource(deletable)
    assert not ResourceItem.objects.filter(pk=resource_id).exists()
    event = AuditEvent.objects.get(event_type="resource.deleted", target_id=str(resource_id))
    assert event.target_snapshot["name"] == "Deletable"
    assert event.target_snapshot["outcome"] == "deleted"


@pytest.mark.django_db
def test_use_submission_dependency_requires_retirement():
    manager = UserFactory(global_role="admin", status="active")
    student = UserFactory(global_role="student", status="active")
    resource = ResourceItem.objects.create(
        resource_type=ResourceType.objects.create(name="Room"), name="Clean room", manager=manager
    )
    ResourceUseSubmission.objects.create(
        resource_item=resource,
        student=student,
        submission_type=ResourceUseSubmission.SubmissionType.REQUEST,
        details="Access",
    )
    with pytest.raises(ValidationError):
        ResourceInventoryService(manager).delete_resource(resource)
    retired = ResourceInventoryService(manager).retire_resource(resource)
    assert retired.status == ResourceItem.Status.RETIRED
