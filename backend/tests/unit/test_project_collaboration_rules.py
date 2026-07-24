import pytest
from django.core.exceptions import ValidationError

from apps.projects.collaboration_services import ensure_teacher_eligible
from tests.factories.accounts import VerifiedUserFactory


@pytest.mark.django_db
def test_only_active_verified_approved_teachers_are_eligible():
    eligible = VerifiedUserFactory(global_role="advisor", active_role="teacher")
    assert ensure_teacher_eligible(eligible) == eligible

    candidates = [
        VerifiedUserFactory(global_role="student", active_role="student"),
        VerifiedUserFactory(global_role="admin", active_role="administrator"),
        VerifiedUserFactory(global_role="advisor", active_role="teacher", status="suspended"),
        VerifiedUserFactory(global_role="advisor", active_role="pending"),
        VerifiedUserFactory(global_role="advisor", active_role="teacher", email_verified_at=None),
    ]
    for candidate in candidates:
        with pytest.raises(ValidationError):
            ensure_teacher_eligible(candidate)

