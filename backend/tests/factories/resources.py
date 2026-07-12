import factory
from django.utils import timezone

from apps.audit.models import AuditEvent
from apps.resources.models import Booking, ResourceItem, ResourceType, ResourceUseSubmission
from tests.factories.accounts import UserFactory
from tests.factories.collaboration import ResearchProjectFactory


class ResourceTypeFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = ResourceType

    name = factory.Sequence(lambda n: f"Resource type {n}")
    confirmation_policy = ResourceType.ConfirmationPolicy.IMMEDIATE


class ResourceItemFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = ResourceItem

    resource_type = factory.SubFactory(ResourceTypeFactory)
    name = factory.Sequence(lambda n: f"Shared resource {n}")
    total_quantity = 1
    manager = factory.SubFactory(UserFactory, global_role="advisor", status="active")


class BookingFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = Booking

    project = factory.SubFactory(ResearchProjectFactory)
    resource_item = factory.SubFactory(ResourceItemFactory)
    requested_by = factory.SubFactory(UserFactory, global_role="student", status="active")
    starts_at = factory.LazyFunction(lambda: timezone.now() + timezone.timedelta(days=1))
    ends_at = factory.LazyAttribute(lambda obj: obj.starts_at + timezone.timedelta(hours=1))


class ResourceUseSubmissionFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = ResourceUseSubmission

    resource_item = factory.SubFactory(ResourceItemFactory)
    student = factory.SubFactory(UserFactory, global_role="student", status="active")
    submission_type = ResourceUseSubmission.SubmissionType.REQUEST
    details = "Request access"


class ResourceAuditSnapshotFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = AuditEvent

    actor = factory.SubFactory(UserFactory, global_role="advisor", status="active")
    event_type = "resource.deleted"
    target_type = "ResourceItem"
    target_id = factory.Sequence(str)
    target_snapshot = factory.LazyAttribute(
        lambda obj: {"resourceId": obj.target_id, "name": "Deleted resource", "outcome": "deleted"}
    )
    summary = "Deleted resource"
