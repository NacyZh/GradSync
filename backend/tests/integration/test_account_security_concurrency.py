import pytest
from django.utils import timezone

from apps.accounts.security_services import consume_password_recovery, issue_password_recovery
from tests.factories.accounts import UserFactory


@pytest.mark.django_db(transaction=True)
def test_consumed_recovery_cannot_be_replayed():
    user = UserFactory(email_verified_at=timezone.now())
    request, token = issue_password_recovery(user=user)
    consume_password_recovery(
        request_id=request.id,
        raw_token=token,
        new_password="Sup3r-New-Password!",
    )
    with pytest.raises(ValueError, match="invalid"):
        consume_password_recovery(
            request_id=request.id,
            raw_token=token,
            new_password="Yet-An0ther-Pw!",
        )
