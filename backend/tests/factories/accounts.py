import factory
from django.contrib.auth import get_user_model
from django.utils import timezone

from apps.accounts.models import AccountSession


class UserFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = get_user_model()

    email = factory.Sequence(lambda n: f"user{n}@example.com")
    name = factory.Faker("name")
    global_role = "student"
    status = "active"
    active_role = factory.LazyAttribute(
        lambda user: {
            "advisor": "teacher",
            "admin": "administrator",
        }.get(user.global_role, "student")
    )
    email_verified_at = factory.LazyFunction(timezone.now)


class VerifiedUserFactory(UserFactory):
    email_verified_at = factory.LazyFunction(timezone.now)


class RestrictedUserFactory(VerifiedUserFactory):
    status = "suspended"


class AccountSessionFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = AccountSession

    user = factory.SubFactory(VerifiedUserFactory)
    device_label = factory.Sequence(lambda n: f"Test browser {n}")
    expires_at = factory.LazyFunction(AccountSession.default_expiry)
