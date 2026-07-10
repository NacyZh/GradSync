import pytest

from apps.submissions.models import WritingParticipant
from apps.submissions.writing_participant_services import ensure_default_writing_participants
from tests.factories.shared_workspace import (
    active_student,
    active_teacher,
    project_with_members,
    writing_item,
)


@pytest.mark.django_db
def test_default_participant_migration_preserves_writing_history_and_adds_roles():
    student = active_student()
    advisor = active_teacher()
    project = project_with_members(advisor=advisor, students=[student])
    writing = writing_item(student=student, project=project, legacy_project=project)

    ensure_default_writing_participants(writing)

    roles = set(
        WritingParticipant.objects.filter(writing_project=writing).values_list(
            "participant_role", flat=True
        )
    )
    writing.refresh_from_db()

    assert roles == {
        WritingParticipant.Role.STUDENT_AUTHOR,
        WritingParticipant.Role.BOUND_ADVISOR,
    }
    assert writing.student == student
    assert writing.legacy_project == project
