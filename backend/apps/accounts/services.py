from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError
from django.db import transaction

User = get_user_model()


class AccountsService:
    """Account provisioning and lifecycle management.

    Only administrators may invoke these operations (enforced at the view layer
    via IsAdministrator permission).
    """

    @staticmethod
    def create_account(*, email: str, name: str, global_role: str, created_by) -> User:
        if User.objects.filter(email=email).exists():
            raise ValidationError("An account with this email already exists.")

        user = User.objects.create(
            email=email,
            name=name,
            global_role=global_role,
            status=User.Status.INVITED,
            is_active=True,
        )
        user.set_unusable_password()
        user.save(update_fields=["password"])
        return user

    @staticmethod
    def edit_account(*, user: User, name: str | None, global_role: str | None) -> User:
        if name is not None:
            user.name = name
        if global_role is not None:
            _guard_last_admin(user, new_role=global_role)
            user.global_role = global_role
        user.save(update_fields=["name", "global_role"])
        return user

    @staticmethod
    def suspend_account(*, user: User, actor) -> User:
        _guard_last_admin(user, new_role=None)
        user.status = User.Status.SUSPENDED
        user.is_active = False
        user.save(update_fields=["status", "is_active"])
        return user

    @staticmethod
    def reactivate_account(*, user: User) -> User:
        user.status = User.Status.ACTIVE
        user.is_active = True
        user.save(update_fields=["status", "is_active"])
        return user

    @staticmethod
    def archive_account(*, user: User, actor) -> User:
        _guard_last_admin(user, new_role=None)
        user.status = User.Status.ARCHIVED
        user.is_active = False
        user.save(update_fields=["status", "is_active"])
        return user


def _guard_last_admin(user: User, new_role: str | None):
    """Prevent the last active administrator from being demoted, suspended, or archived.

    Called before any role change, suspend, or archive action on an admin account.
    When `new_role` is None the action is a status change (suspend/archive), not a role change.
    """
    if not user.is_administrator:
        return  # Target is not an admin — no restriction.

    # If the action changes the role to non-admin, it's a demotion.
    would_lose_admin_role = new_role is not None and new_role != User.GlobalRole.ADMIN
    # If new_role is None, this is a suspend/archive — admin role is preserved
    # but the account becomes inactive.
    would_lose_active_admin = new_role is None

    if would_lose_admin_role or would_lose_active_admin:
        active_admin_count = User.objects.filter(
            global_role=User.GlobalRole.ADMIN, status=User.Status.ACTIVE
        ).count()
        if active_admin_count <= 1:
            raise ValidationError(
                "Cannot remove, demote, suspend, or archive the last active administrator. "
                "Promote another user to administrator first."
            )
