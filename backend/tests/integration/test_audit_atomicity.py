import pytest
from django.db import transaction

from tests.factories.accounts import UserFactory


@pytest.mark.django_db(transaction=True)
def test_required_audit_failure_rolls_back_privileged_change(monkeypatch):
    from apps.audit.services import audited_mutation

    user = UserFactory(name="Before")

    def mutation():
        user.name = "After"
        user.save(update_fields=["name"])
        return user

    monkeypatch.setattr(
        "apps.audit.services.record_event",
        lambda *args, **kwargs: (_ for _ in ()).throw(RuntimeError("audit unavailable")),
    )

    with pytest.raises(RuntimeError, match="audit unavailable"):
        with transaction.atomic():
            audited_mutation(
                mutation,
                project=None,
                actor=user,
                event_type="account_security.test",
                summary="Test",
            )

    user.refresh_from_db()
    assert user.name == "Before"
