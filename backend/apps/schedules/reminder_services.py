from zoneinfo import ZoneInfo

from django.db import transaction
from django.db.models import Prefetch
from django.utils import timezone

from apps.notifications.models import (
    Notification,
    NotificationCategoryPreference,
    NotificationDeliveryAttempt,
    NotificationPreferenceProfile,
)
from apps.notifications.policy_services import quiet_hours_eligible_at_for_profile
from apps.notifications.services import enqueue_notification

from .models import ScheduleItem, ScheduleNotificationDispatch, ScheduleRecipientGrant
from .recurrence import expand_occurrences


def _action_path(item):
    date_value = item.starts_on or item.starts_at.date()
    occurrence_key = item.starts_on.isoformat() if item.all_day else item.starts_at.isoformat()
    return f"/?date={date_value.isoformat()}&item=schedule%3A{item.id}%3A{occurrence_key}"


@transaction.atomic
def _create_reminder_notifications(
    *,
    item,
    project,
    occurrence_key,
    offset_minutes,
    claims,
    eligible_at,
):
    if not claims:
        return 0

    recipient_ids = [recipient.id for recipient, _dispatch in claims]
    profiles = {
        profile.user_id: profile
        for profile in NotificationPreferenceProfile.objects.filter(
            user_id__in=recipient_ids
        ).prefetch_related("category_preferences")
    }
    missing_profile_ids = [
        recipient_id for recipient_id in recipient_ids if recipient_id not in profiles
    ]
    if missing_profile_ids:
        NotificationPreferenceProfile.objects.bulk_create(
            [
                NotificationPreferenceProfile(user_id=recipient_id)
                for recipient_id in missing_profile_ids
            ],
            ignore_conflicts=True,
        )
        profiles = {
            profile.user_id: profile
            for profile in NotificationPreferenceProfile.objects.filter(
                user_id__in=recipient_ids
            ).prefetch_related("category_preferences")
        }

    existing_preferences = {
        (preference.profile_id, preference.category)
        for profile in profiles.values()
        for preference in profile.category_preferences.all()
    }
    missing_preferences = [
        NotificationCategoryPreference(profile=profile, category=category)
        for profile in profiles.values()
        for category in Notification.Category.values
        if (profile.id, category) not in existing_preferences
    ]
    if missing_preferences:
        NotificationCategoryPreference.objects.bulk_create(
            missing_preferences,
            ignore_conflicts=True,
        )
    schedule_email_enabled = {
        preference.profile.user_id: preference.email_enabled
        for preference in NotificationCategoryPreference.objects.filter(
            profile__user_id__in=recipient_ids,
            category=Notification.Category.SCHEDULE,
        ).select_related("profile")
    }

    action_path = _action_path(item)
    notifications = []
    delivery_values = []
    for recipient, _dispatch in claims:
        profile = profiles[recipient.id]
        email_eligible_at = quiet_hours_eligible_at_for_profile(profile, eligible_at)
        email_enabled = schedule_email_enabled.get(recipient.id, True)
        notification = Notification(
            project=project,
            recipient=recipient,
            recipient_email=recipient.email,
            sender=item.organizer,
            event_type=Notification.EventType.SCHEDULE_REMINDER,
            target_type="ScheduleItem",
            target_id=str(item.id),
            subject="Schedule reminder",
            action_path=action_path,
            status=(
                Notification.Status.PENDING
                if email_enabled
                else Notification.Status.IN_APP_ONLY
            ),
            delivery_policy=Notification.DeliveryPolicy.IN_APP_EMAIL,
            eligible_at=email_eligible_at if email_enabled else eligible_at,
            category=Notification.Category.SCHEDULE,
            requirement_type=Notification.RequirementType.INFORMATIONAL,
            outcome_state=Notification.OutcomeState.NOT_REQUIRED,
        )
        notifications.append(notification)
        delivery_values.append((email_enabled, email_eligible_at))
    Notification.objects.bulk_create(notifications)

    attempts = []
    completed_at = timezone.now()
    for notification, (email_enabled, email_eligible_at) in zip(
        notifications, delivery_values, strict=True
    ):
        attempts.extend(
            [
                NotificationDeliveryAttempt(
                    notification=notification,
                    channel=NotificationDeliveryAttempt.Channel.IN_APP,
                    attempt_number=1,
                    state=NotificationDeliveryAttempt.State.SENT,
                    eligible_at=eligible_at,
                    attempted_at=notification.created_at,
                    completed_at=notification.created_at,
                    idempotency_key=f"notification:{notification.pk}:in_app:1",
                ),
                NotificationDeliveryAttempt(
                    notification=notification,
                    channel=NotificationDeliveryAttempt.Channel.EMAIL,
                    attempt_number=1,
                    state=(
                        NotificationDeliveryAttempt.State.PENDING
                        if email_enabled
                        else NotificationDeliveryAttempt.State.SKIPPED
                    ),
                    eligible_at=email_eligible_at,
                    completed_at=None if email_enabled else completed_at,
                    failure_code="" if email_enabled else "preference_disabled",
                    idempotency_key=f"notification:{notification.pk}:email:1",
                ),
            ]
        )
    NotificationDeliveryAttempt.objects.bulk_create(attempts)

    in_app_dispatches = []
    email_dispatches = []
    for (_recipient, dispatch), notification in zip(claims, notifications, strict=True):
        dispatch.notification = notification
        dispatch.status = ScheduleNotificationDispatch.Status.CREATED
        in_app_dispatches.append(dispatch)
        email_dispatches.append(
            ScheduleNotificationDispatch(
                schedule_item=item,
                recipient_id=notification.recipient_id,
                occurrence_key=occurrence_key,
                event_type=ScheduleNotificationDispatch.EventType.REMINDER,
                offset_minutes=offset_minutes,
                offset_key=offset_minutes,
                channel=ScheduleNotificationDispatch.Channel.EMAIL,
                notification=notification,
                status=ScheduleNotificationDispatch.Status.CLAIMED,
            )
        )
    ScheduleNotificationDispatch.objects.bulk_update(
        in_app_dispatches,
        ["notification", "status", "updated_at"],
    )
    ScheduleNotificationDispatch.objects.bulk_create(email_dispatches, ignore_conflicts=True)
    return len(notifications)


def dispatch_group_event(item, *, actor, event_type, recipients=None):
    event_map = {
        "published": Notification.EventType.SCHEDULE_PUBLISHED,
        "changed": Notification.EventType.SCHEDULE_CHANGED,
        "cancelled": Notification.EventType.SCHEDULE_CANCELLED,
        "removed": Notification.EventType.SCHEDULE_RECIPIENT_REMOVED,
    }
    policy = (
        Notification.DeliveryPolicy.IN_APP_EMAIL
        if event_type == "cancelled"
        else Notification.DeliveryPolicy.IN_APP
    )
    project = next(
        (audience.project for audience in item.audiences.all() if audience.project_id), None
    )
    created = 0
    recipient_list = recipients
    if recipient_list is None:
        recipient_list = [
            grant.recipient
            for grant in item.recipient_grants.filter(valid_until__isnull=True).select_related(
                "recipient"
            )
        ]
    for recipient in recipient_list:
        dispatch, was_created = ScheduleNotificationDispatch.objects.get_or_create(
            schedule_item=item,
            recipient=recipient,
            occurrence_key=f"series:{item.version}",
            event_type=event_type,
            channel=ScheduleNotificationDispatch.Channel.IN_APP,
            defaults={"status": ScheduleNotificationDispatch.Status.CLAIMED},
        )
        if not was_created:
            continue
        notification = enqueue_notification(
            project=project,
            recipient=recipient,
            sender=actor,
            event_type=event_map[event_type],
            target_type="ScheduleItem",
            target_id=str(item.id),
            subject={
                "published": "New group schedule",
                "changed": "Group schedule changed",
                "cancelled": "Group schedule cancelled",
                "removed": "Schedule audience changed",
            }[event_type],
            action_path=_action_path(item),
            eligible_at=timezone.now(),
            delivery_policy=policy,
        )
        dispatch.notification = notification
        dispatch.status = ScheduleNotificationDispatch.Status.CREATED
        dispatch.save(update_fields=["notification", "status", "updated_at"])
        if event_type == "cancelled":
            ScheduleNotificationDispatch.objects.get_or_create(
                schedule_item=item,
                recipient=recipient,
                occurrence_key=f"series:{item.version}",
                event_type=event_type,
                channel=ScheduleNotificationDispatch.Channel.EMAIL,
                defaults={
                    "notification": notification,
                    "status": ScheduleNotificationDispatch.Status.CLAIMED,
                },
            )
        created += 1
    return created


def create_due_schedule_reminders(*, now=None, limit=500):
    now = now or timezone.now()
    created = 0
    reminders = (
        ScheduleItem.objects.filter(status=ScheduleItem.Status.ACTIVE)
        .exclude(reminders__isnull=True)
        .select_related("owner", "organizer")
        .prefetch_related(
            "reminders",
            Prefetch(
                "recipient_grants",
                queryset=ScheduleRecipientGrant.objects.select_related("recipient"),
            ),
            "exceptions",
            "audiences__project",
        )
        .distinct()[:limit]
    )
    for item in reminders:
        from .audience_services import reresolve_audience

        if item.scope == ScheduleItem.Scope.GROUP:
            reresolve_audience(item, resolved_at=now)
        for reminder in item.reminders.all():
            window_start = now + timezone.timedelta(minutes=reminder.offset_minutes - 5)
            window_end = now + timezone.timedelta(minutes=reminder.offset_minutes + 5)
            expansion_start = window_start.date() if item.all_day else window_start
            expansion_end = (
                (window_end + timezone.timedelta(days=1)).date() if item.all_day else window_end
            )
            occurrences = expand_occurrences(
                starts_at=item.starts_at,
                ends_at=item.ends_at,
                starts_on=item.starts_on,
                ends_on=item.ends_on,
                timezone_name=item.timezone,
                frequency=item.recurrence_frequency,
                interval=item.recurrence_interval,
                weekdays=item.recurrence_weekdays,
                until=item.recurrence_until,
                window_start=expansion_start,
                window_end=expansion_end,
            )
            for occurrence in occurrences:
                occurrence_start = occurrence.starts_at or timezone.make_aware(
                    timezone.datetime.combine(occurrence.starts_on, timezone.datetime.min.time()),
                    ZoneInfo(item.timezone),
                )
                due_at = occurrence_start - timezone.timedelta(minutes=reminder.offset_minutes)
                if (
                    not now - timezone.timedelta(minutes=5)
                    <= due_at
                    <= now + timezone.timedelta(minutes=5)
                ):
                    continue
                occurrence_key = (
                    occurrence.starts_on.isoformat()
                    if item.all_day
                    else occurrence.starts_at.isoformat()
                )
                exception = next(
                    (
                        value
                        for value in item.exceptions.all()
                        if (item.all_day and value.original_starts_on == occurrence.starts_on)
                        or (not item.all_day and value.original_starts_at == occurrence.starts_at)
                    ),
                    None,
                )
                if exception and exception.status in {"cancelled", "completed"}:
                    continue
                if item.scope == ScheduleItem.Scope.PERSONAL:
                    recipients = [item.owner] if item.owner.status == "active" else []
                else:
                    recipients = [
                        grant.recipient
                        for grant in item.recipient_grants.all()
                        if grant.recipient.status == "active"
                        and grant.valid_from <= occurrence_start
                        and (grant.valid_until is None or grant.valid_until > occurrence_start)
                    ]
                project = next(
                    (audience.project for audience in item.audiences.all() if audience.project_id),
                    None,
                )
                claims = []
                for recipient in recipients:
                    dispatch, was_created = ScheduleNotificationDispatch.objects.get_or_create(
                        schedule_item=item,
                        recipient=recipient,
                        occurrence_key=occurrence_key,
                        event_type=ScheduleNotificationDispatch.EventType.REMINDER,
                        offset_minutes=reminder.offset_minutes,
                        channel=ScheduleNotificationDispatch.Channel.IN_APP,
                        defaults={"status": ScheduleNotificationDispatch.Status.CLAIMED},
                    )
                    if not was_created:
                        continue
                    claims.append((recipient, dispatch))
                created += _create_reminder_notifications(
                    item=item,
                    project=project,
                    occurrence_key=occurrence_key,
                    offset_minutes=reminder.offset_minutes,
                    claims=claims,
                    eligible_at=now,
                )
    return created
