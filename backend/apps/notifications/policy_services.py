from datetime import UTC, datetime, timedelta
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

from django.conf import settings
from django.core.exceptions import PermissionDenied, ValidationError
from django.db import transaction
from django.utils import timezone

from apps.audit.services import record_execution_event
from apps.common.concurrency import VersionConflict, require_expected_version
from apps.projects.access_services import project_capabilities

from .models import (
    Notification,
    NotificationCategoryPreference,
    NotificationPreferenceProfile,
    ProjectNotificationPolicy,
)

MANDATORY_EMAIL_CATEGORIES = {Notification.Category.SECURITY}


def preference_profile_for(user):
    profile, _ = NotificationPreferenceProfile.objects.get_or_create(user=user)
    existing = {
        item.category: item
        for item in profile.category_preferences.all()
    }
    NotificationCategoryPreference.objects.bulk_create(
        [
            NotificationCategoryPreference(profile=profile, category=category)
            for category, _ in Notification.Category.choices
            if category not in existing
        ],
        ignore_conflicts=True,
    )
    return NotificationPreferenceProfile.objects.prefetch_related(
        "category_preferences"
    ).get(pk=profile.pk)


@transaction.atomic
def update_preference_profile(
    *,
    user,
    expected_version: int,
    quiet_hours_enabled: bool,
    quiet_hours_start=None,
    quiet_hours_end=None,
    timezone_name: str,
    category_email: dict[str, bool],
):
    profile = NotificationPreferenceProfile.objects.select_for_update().filter(
        user=user
    ).first()
    if profile is None:
        profile = preference_profile_for(user)
    require_expected_version(
        profile,
        expected_version,
        safe_state=lambda current: {"id": current.pk, "version": current.version},
    )
    try:
        ZoneInfo(timezone_name)
    except ZoneInfoNotFoundError as exc:
        raise ValidationError("Timezone is invalid.") from exc
    profile.quiet_hours_enabled = quiet_hours_enabled
    profile.quiet_hours_start = quiet_hours_start
    profile.quiet_hours_end = quiet_hours_end
    profile.timezone_name = timezone_name
    profile.version += 1
    profile.full_clean()
    profile.save()
    for category, enabled in category_email.items():
        if category not in Notification.Category.values:
            raise ValidationError("Notification category is invalid.")
        if category in MANDATORY_EMAIL_CATEGORIES and not enabled:
            raise ValidationError("Security email delivery cannot be disabled.")
        NotificationCategoryPreference.objects.update_or_create(
            profile=profile,
            category=category,
            defaults={"email_enabled": enabled},
        )
    return preference_profile_for(user)


def email_enabled_for(user, category: str) -> bool:
    if category in MANDATORY_EMAIL_CATEGORIES:
        return True
    profile = preference_profile_for(user)
    preference = next(
        (item for item in profile.category_preferences.all() if item.category == category),
        None,
    )
    return preference.email_enabled if preference else True


def quiet_hours_eligible_at(user, candidate=None):
    candidate = candidate or timezone.now()
    profile = preference_profile_for(user)
    if not profile.quiet_hours_enabled:
        return candidate
    zone = ZoneInfo(profile.timezone_name)
    local = candidate.astimezone(zone)
    start = profile.quiet_hours_start
    end = profile.quiet_hours_end
    if start is None or end is None or start == end:
        return candidate
    local_time = local.timetz().replace(tzinfo=None)
    inside = (
        start <= local_time < end
        if start < end
        else local_time >= start or local_time < end
    )
    if not inside:
        return candidate
    end_date = local.date()
    if start > end and local_time >= start:
        end_date += timedelta(days=1)
    local_end = datetime.combine(end_date, end, tzinfo=zone)
    return local_end.astimezone(UTC)


def _default_policy_values():
    return {
        "reminder_lead_minutes": settings.GRADSYNC_NOTIFICATION_REMINDER_LEAD_MINUTES,
        "escalation_delay_minutes": settings.GRADSYNC_NOTIFICATION_ESCALATION_DELAY_MINUTES,
        "repeat_interval_minutes": settings.GRADSYNC_NOTIFICATION_REPEAT_INTERVAL_MINUTES,
        "max_reminders": settings.GRADSYNC_NOTIFICATION_MAX_REMINDERS,
    }


def project_policy_for(project):
    try:
        return project.notification_policy
    except ProjectNotificationPolicy.DoesNotExist:
        return None


def effective_project_policy(project):
    policy = project_policy_for(project)
    return {
        **_default_policy_values(),
        **(
            {
                "reminder_lead_minutes": policy.reminder_lead_minutes,
                "escalation_delay_minutes": policy.escalation_delay_minutes,
                "repeat_interval_minutes": policy.repeat_interval_minutes,
                "max_reminders": policy.max_reminders,
            }
            if policy
            else {}
        ),
        "version": policy.version if policy else 0,
        "uses_system_defaults": policy is None,
    }


def validate_project_policy_values(values):
    lower = settings.GRADSYNC_NOTIFICATION_THRESHOLD_MIN_MINUTES
    upper = settings.GRADSYNC_NOTIFICATION_THRESHOLD_MAX_MINUTES
    for field in (
        "reminder_lead_minutes",
        "escalation_delay_minutes",
        "repeat_interval_minutes",
    ):
        if not lower <= values[field] <= upper:
            raise ValidationError({field: f"Must be between {lower} and {upper} minutes."})
    if not 0 <= values["max_reminders"] <= 20:
        raise ValidationError({"max_reminders": "Must be between 0 and 20."})


@transaction.atomic
def update_project_policy(*, actor, project, expected_version: int, **values):
    if not project_capabilities(actor, project)["canManageProjectNotificationPolicy"]:
        raise PermissionDenied("Only the active primary advisor can update this policy.")
    policy = ProjectNotificationPolicy.objects.select_for_update().filter(
        project=project
    ).first()
    if policy is None:
        if expected_version != 0:
            raise VersionConflict({"projectId": project.pk, "version": 0})
        effective = _default_policy_values() | values
        validate_project_policy_values(effective)
        created = ProjectNotificationPolicy.objects.create(
            project=project,
            updated_by=actor,
            **effective,
        )
        record_execution_event(
            project=project,
            actor=actor,
            action="notification_policy.created",
            target=created,
            state={"version": created.version},
            privileged=True,
        )
        return created
    require_expected_version(
        policy,
        expected_version,
        safe_state=lambda current: {"projectId": project.pk, "version": current.version},
    )
    effective = {
        "reminder_lead_minutes": policy.reminder_lead_minutes,
        "escalation_delay_minutes": policy.escalation_delay_minutes,
        "repeat_interval_minutes": policy.repeat_interval_minutes,
        "max_reminders": policy.max_reminders,
    } | values
    validate_project_policy_values(effective)
    for field, value in effective.items():
        setattr(policy, field, value)
    policy.updated_by = actor
    policy.version += 1
    policy.save()
    record_execution_event(
        project=project,
        actor=actor,
        action="notification_policy.updated",
        target=policy,
        state={"version": policy.version},
        privileged=True,
    )
    return policy
