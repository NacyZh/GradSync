import factory
from django.contrib.auth import get_user_model
from django.utils import timezone

from apps.accounts.models import RoleActivationRequest, StudentProfile
from apps.common.models import UploadedFile
from tests.factories.accounts import UserFactory


class StudentProfileFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = StudentProfile

    user = factory.SubFactory(UserFactory, global_role="student")
    degree_type = StudentProfile.DegreeType.MASTERS


class RoleActivationRequestFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = RoleActivationRequest

    user = factory.SubFactory(UserFactory, global_role="advisor", status="invited")
    requested_role = RoleActivationRequest.RequestedRole.TEACHER
    activation_source = RoleActivationRequest.ActivationSource.ADMIN_APPROVAL
    status = RoleActivationRequest.Status.PENDING
    expires_at = factory.LazyFunction(lambda: timezone.now() + timezone.timedelta(days=14))


class UploadedFileFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = UploadedFile

    owner = factory.SubFactory(UserFactory)
    category = UploadedFile.Category.PAPER
    original_filename = factory.Sequence(lambda n: f"upload-{n}.pdf")
    stored_name = factory.Sequence(lambda n: f"collaboration/paper/upload-{n}.pdf")
    content_type = "application/pdf"
    size_bytes = 1024
    checksum_sha256 = factory.Sequence(lambda n: f"{n:064x}"[-64:])


def writing_project_payload(**overrides):
    payload = {"title": "Thesis Draft", "description": "Chapter review"}
    payload.update(overrides)
    return payload


def document_category_payload(**overrides):
    payload = {"name": "Protocols", "description": "Lab operating documents"}
    payload.update(overrides)
    return payload


def resource_use_submission_payload(**overrides):
    payload = {"purpose": "Instrument use", "notes": "Two-hour reservation"}
    payload.update(overrides)
    return payload
