import factory
from django.utils import timezone

from apps.accounts.models import RoleActivationRequest, StudentProfile
from apps.common.models import UploadedFile
from apps.library.models import PaperFile, PaperRecord
from apps.projects.models import ProjectMembership, ResearchProject
from apps.submissions.models import TeacherFeedback, WritingProject, WritingVersion
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


class ActiveResearchUserFactory(UserFactory):
    global_role = "student"
    status = "active"


class PaperLibraryMaintainerFactory(UserFactory):
    global_role = "advisor"
    status = "active"


class PaperLibraryNonMaintainerFactory(UserFactory):
    global_role = "student"
    status = "active"


class ResearchProjectFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = ResearchProject

    title = factory.Sequence(lambda n: f"Research Project {n}")
    advisor = factory.SubFactory(UserFactory, global_role="advisor", status="active")


class PaperRecordFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = PaperRecord

    project = factory.SubFactory(ResearchProjectFactory)
    title = factory.Sequence(lambda n: f"Shared Paper {n}")
    canonical_title = factory.SelfAttribute("title")
    authors = factory.LazyFunction(lambda: ["Ada Lovelace"])
    publication_year = 2026
    visibility = PaperRecord.Visibility.GROUP_WIDE
    uploaded_file = factory.SubFactory(UploadedFileFactory)
    checksum_sha256 = factory.SelfAttribute("uploaded_file.checksum_sha256")
    created_by = factory.SelfAttribute("project.advisor")
    status = PaperRecord.Status.ACTIVE


class PaperFileFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = PaperFile

    paper = factory.SubFactory(PaperRecordFactory)
    uploaded_file = factory.SubFactory(UploadedFileFactory)
    original_filename = factory.Sequence(lambda n: f"paper-{n}.pdf")
    default_download_filename = factory.Sequence(lambda n: f"Shared Paper {n}.pdf")
    content_type = "application/pdf"
    size_bytes = 1024
    file_fingerprint = factory.Sequence(lambda n: f"paper-file-{n:011d}")
    validation_status = PaperFile.ValidationStatus.VALID
    uploaded_by = factory.SelfAttribute("paper.created_by")


def active_shared_pdf_paper(**overrides):
    paper = PaperRecordFactory(**overrides)
    if not hasattr(paper.uploaded_file, "paper_file_record"):
        PaperFileFactory(paper=paper, uploaded_file=paper.uploaded_file)
    return paper


class ProjectMembershipFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = ProjectMembership

    project = factory.SubFactory(ResearchProjectFactory)
    user = factory.SubFactory(UserFactory)
    role = ProjectMembership.Role.STUDENT
    status = ProjectMembership.Status.ACTIVE


class WritingProjectFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = WritingProject

    project = factory.SubFactory(ResearchProjectFactory)
    student = factory.SubFactory(UserFactory, global_role="student", status="active")
    title = factory.Sequence(lambda n: f"Thesis Draft {n}")
    writing_type = WritingProject.WritingType.THESIS


class WritingVersionFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = WritingVersion

    writing_project = factory.SubFactory(WritingProjectFactory)
    version_number = factory.Sequence(lambda n: n + 1)
    submitted_by = factory.SelfAttribute("writing_project.student")
    draft_file = factory.SubFactory(
        UploadedFileFactory,
        category=UploadedFile.Category.WRITING,
        original_filename="draft.docx",
        stored_name="collaboration/writing/draft.docx",
    )
    file_kind = WritingVersion.FileKind.WORD
    summary = "Initial version"


class TeacherFeedbackFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = TeacherFeedback

    writing_version = factory.SubFactory(WritingVersionFactory)
    reviewer = factory.SubFactory(UserFactory, global_role="advisor", status="active")
    comments = "Reviewed"
    annotated_file = factory.SubFactory(
        UploadedFileFactory,
        category=UploadedFile.Category.FEEDBACK,
        original_filename="annotated.docx",
        stored_name="collaboration/feedback/annotated.docx",
    )
    status = TeacherFeedback.Status.NOTIFICATION_PENDING


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
