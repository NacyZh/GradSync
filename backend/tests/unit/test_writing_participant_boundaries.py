import pytest

from apps.submissions.models import WritingParticipant
from apps.submissions.permissions import can_access_writing_project
from tests.factories.shared_workspace import (
    active_admin,
    active_student,
    active_teacher,
    writing_item,
)


@pytest.mark.django_db
def test_writing_access_allows_student_author_bound_advisor_assigned_reviewer_and_admin():
    student = active_student()
    bound_advisor = active_teacher()
    reviewer = active_teacher()
    admin = active_admin()
    writing = writing_item(student=student)
    WritingParticipant.objects.create(
        writing_project=writing,
        user=bound_advisor,
        participant_role=WritingParticipant.Role.BOUND_ADVISOR,
    )
    WritingParticipant.objects.create(
        writing_project=writing,
        user=reviewer,
        participant_role=WritingParticipant.Role.ASSIGNED_REVIEWER,
    )

    assert can_access_writing_project(student, writing)
    assert can_access_writing_project(bound_advisor, writing)
    assert can_access_writing_project(reviewer, writing)
    assert can_access_writing_project(admin, writing)


@pytest.mark.django_db
def test_writing_access_denies_different_teacher_unrelated_member_and_removed_participant():
    student = active_student()
    different_teacher = active_teacher()
    unrelated_student = active_student()
    removed_reviewer = active_teacher()
    writing = writing_item(student=student)
    WritingParticipant.objects.create(
        writing_project=writing,
        user=removed_reviewer,
        participant_role=WritingParticipant.Role.ASSIGNED_REVIEWER,
        status=WritingParticipant.Status.REMOVED,
    )

    assert not can_access_writing_project(different_teacher, writing)
    assert not can_access_writing_project(unrelated_student, writing)
    assert not can_access_writing_project(removed_reviewer, writing)
