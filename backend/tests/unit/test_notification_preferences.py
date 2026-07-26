from datetime import UTC, time

import pytest
from django.core.exceptions import ValidationError
from django.utils import timezone

from apps.notifications.models import Notification
from apps.notifications.policy_services import (
    email_enabled_for,
    quiet_hours_eligible_at,
    update_preference_profile,
)
from tests.factories.accounts import VerifiedUserFactory

pytestmark = pytest.mark.django_db


def test_quiet_hours_defer_email_in_recipient_timezone():
    user = VerifiedUserFactory()
    update_preference_profile(
        user=user,
        expected_version=1,
        quiet_hours_enabled=True,
        quiet_hours_start=time(22),
        quiet_hours_end=time(7),
        timezone_name="Asia/Shanghai",
        category_email={Notification.Category.PROJECT: True},
    )
    candidate = timezone.datetime(2026, 7, 24, 15, 0, tzinfo=UTC)
    assert quiet_hours_eligible_at(user, candidate) > candidate


def test_security_email_cannot_be_disabled():
    user = VerifiedUserFactory()
    with pytest.raises(ValidationError):
        update_preference_profile(
            user=user,
            expected_version=1,
            quiet_hours_enabled=False,
            timezone_name="UTC",
            category_email={Notification.Category.SECURITY: False},
        )
    assert email_enabled_for(user, Notification.Category.SECURITY) is True
