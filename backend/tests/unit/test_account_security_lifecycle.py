from datetime import timedelta

import pytest
from django.utils import timezone

from apps.accounts.models import AccountRecoveryRequest, EmailChangeRequest
from apps.accounts.security_services import (
    consume_password_recovery,
    issue_email_change,
    issue_password_recovery,
)
from tests.factories.accounts import UserFactory

PASSWORD = "Sup3r-Secret-Pw!"
NEW_PASSWORD = "An0ther-Secure-Pw!"


@pytest.mark.django_db
def test_recovery_stores_only_hash_and_supersedes_previous_request():
    user = UserFactory(email_verified_at=timezone.now())
    user.set_password(PASSWORD)
    user.save()

    first, first_token = issue_password_recovery(user=user)
    second, second_token = issue_password_recovery(user=user)

    first.refresh_from_db()
    assert first.status == AccountRecoveryRequest.Status.SUPERSEDED
    assert first.token_hash != first_token
    assert second.token_hash != second_token
    with pytest.raises(ValueError, match="invalid"):
        consume_password_recovery(
            request_id=first.id,
            raw_token=first_token,
            new_password=NEW_PASSWORD,
        )


@pytest.mark.django_db
def test_expired_recovery_and_email_change_are_not_consumable():
    user = UserFactory(email_verified_at=timezone.now())
    user.set_password(PASSWORD)
    user.save()
    recovery, token = issue_password_recovery(user=user)
    AccountRecoveryRequest.objects.filter(pk=recovery.pk).update(
        expires_at=timezone.now() - timedelta(seconds=1)
    )
    with pytest.raises(ValueError, match="invalid"):
        consume_password_recovery(
            request_id=recovery.id,
            raw_token=token,
            new_password=NEW_PASSWORD,
        )

    change, _code = issue_email_change(
        user=user,
        new_email="new@example.com",
        current_password=PASSWORD,
    )
    EmailChangeRequest.objects.filter(pk=change.pk).update(
        expires_at=timezone.now() - timedelta(seconds=1)
    )
    change.refresh_from_db()
    assert not change.is_usable()
