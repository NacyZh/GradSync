from copy import copy
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo

from django.core.exceptions import PermissionDenied, ValidationError
from django.db import transaction
from django.db.models import Max
from django.utils import timezone

from .models import (
    ScheduleAudience,
    ScheduleItem,
    ScheduleOccurrenceException,
    ScheduleRecipientGrant,
    ScheduleReminder,
    ScheduleRevision,
)
from .permissions import can_manage_group_item, can_publish_group_item


class ScheduleVersionConflict(Exception):
    def __init__(self, item):
        self.item = item
        super().__init__("This schedule changed since it was opened.")


def _assert_owner(actor, item):
    if item.owner_id != actor.id:
        raise PermissionDenied("Only the schedule owner can change this item.")


def _assert_can_change(actor, item):
    if item.scope == ScheduleItem.Scope.PERSONAL:
        _assert_owner(actor, item)
    elif not can_manage_group_item(actor, item):
        raise PermissionDenied("Only the publisher or an administrator can change this schedule.")


def _assert_version(item, expected_version):
    if item.version != expected_version:
        raise ScheduleVersionConflict(item)


def _apply_fields(item, fields):
    recurrence = fields.pop("recurrence", None)
    reminders = fields.pop("reminders", None)
    for name, value in fields.items():
        setattr(item, name, value)
    if recurrence is not None:
        item.recurrence_frequency = recurrence.get("frequency", "none")
        item.recurrence_interval = recurrence.get("interval", 1)
        item.recurrence_weekdays = recurrence.get("weekdays", [])
        item.recurrence_until = recurrence.get("until")
    return reminders


def _replace_reminders(item, reminders):
    if reminders is None:
        return
    item.reminders.all().delete()
    for reminder in reminders:
        ScheduleReminder.objects.create(
            schedule_item=item,
            offset_minutes=reminder["offset_minutes"],
            mandatory=reminder.get("mandatory", False),
        )


def _record_group_revision(item, actor, change_type, changed_fields, effective_from=""):
    revision_number = (item.revisions.aggregate(maximum=Max("revision_number"))["maximum"] or 0) + 1
    return ScheduleRevision.objects.create(
        schedule_item=item,
        revision_number=revision_number,
        actor=actor,
        change_type=change_type,
        changed_fields=sorted(changed_fields),
        effective_from=effective_from or "",
    )


@transaction.atomic
def create_schedule(*, actor, data):
    fields = dict(data)
    scope = fields.pop("scope", ScheduleItem.Scope.PERSONAL)
    audience = fields.pop("audience", None)
    fields.pop("confirm_conflicts", None)
    if scope == ScheduleItem.Scope.GROUP and not can_publish_group_item(actor):
        raise PermissionDenied("Only advisors and administrators can publish group schedules.")
    item = ScheduleItem(
        owner=actor,
        organizer=actor,
        scope=scope,
        published_at=timezone.now() if scope == ScheduleItem.Scope.GROUP else None,
    )
    reminders = _apply_fields(item, fields)
    item.save()
    _replace_reminders(item, reminders)
    if scope == ScheduleItem.Scope.GROUP:
        from apps.audit.services import record_schedule_event

        from .audience_services import resolve_audience
        from .models import ScheduleRevision
        from .reminder_services import dispatch_group_event

        summary = resolve_audience(
            actor=actor,
            item=item,
            project_ids=(audience or {}).get("project_ids", []),
            account_ids=(audience or {}).get("account_ids", []),
        )
        ScheduleRevision.objects.create(
            schedule_item=item,
            revision_number=1,
            actor=actor,
            change_type=ScheduleRevision.ChangeType.PUBLISHED,
            changed_fields=["scope", "audience"],
            audience_summary=summary,
        )
        record_schedule_event(
            actor=actor,
            schedule_item=item,
            action="published",
            outcome="success",
            audience=summary,
        )
        dispatch_group_event(item, actor=actor, event_type="published")
    return item


@transaction.atomic
def publish_schedule(*, item, actor, expected_version, audience, reminders=None):
    locked = ScheduleItem.objects.select_for_update().get(pk=item.pk)
    _assert_owner(actor, locked)
    _assert_version(locked, expected_version)
    if locked.scope != ScheduleItem.Scope.PERSONAL or not can_publish_group_item(actor):
        raise PermissionDenied("Only owned private schedules can be published.")
    locked.scope = ScheduleItem.Scope.GROUP
    locked.published_at = timezone.now()
    locked.version += 1
    locked.save()
    _replace_reminders(locked, reminders)

    from apps.audit.services import record_schedule_event

    from .audience_services import resolve_audience
    from .models import ScheduleRevision
    from .reminder_services import dispatch_group_event

    summary = resolve_audience(
        actor=actor,
        item=locked,
        project_ids=audience.get("project_ids", []),
        account_ids=audience.get("account_ids", []),
    )
    ScheduleRevision.objects.create(
        schedule_item=locked,
        revision_number=1,
        actor=actor,
        change_type=ScheduleRevision.ChangeType.PUBLISHED,
        changed_fields=["scope", "audience"],
        audience_summary=summary,
    )
    record_schedule_event(
        actor=actor,
        schedule_item=locked,
        action="published",
        outcome="success",
        audience=summary,
    )
    dispatch_group_event(locked, actor=actor, event_type="published")
    return locked


def _parse_occurrence_key(item, occurrence_key):
    if not occurrence_key:
        raise ValidationError({"occurrenceKey": "Select an occurrence."})
    try:
        if item.all_day:
            return datetime.fromisoformat(occurrence_key).date()
        value = datetime.fromisoformat(occurrence_key.replace("Z", "+00:00"))
        if timezone.is_naive(value):
            value = timezone.make_aware(value, ZoneInfo(item.timezone))
        return value
    except ValueError as exc:
        raise ValidationError({"occurrenceKey": "Enter a valid occurrence key."}) from exc


def _exception_for(item, occurrence_key, actor):
    value = _parse_occurrence_key(item, occurrence_key)
    lookup = {"original_starts_on": value} if item.all_day else {"original_starts_at": value}
    exception, _ = ScheduleOccurrenceException.objects.get_or_create(
        schedule_item=item,
        defaults={"created_by": actor},
        **lookup,
    )
    return exception


def _apply_exception_fields(exception, fields):
    if "title" in fields:
        exception.override_title = fields["title"]
    if "description" in fields:
        exception.override_description = fields["description"]
    if fields.get("all_day"):
        exception.override_starts_on = fields.get("starts_on")
        exception.override_ends_on = fields.get("ends_on")
        exception.override_starts_at = None
        exception.override_ends_at = None
    elif "starts_at" in fields or "ends_at" in fields:
        exception.override_starts_at = fields.get("starts_at")
        exception.override_ends_at = fields.get("ends_at")
        exception.override_starts_on = None
        exception.override_ends_on = None
    exception.status = ScheduleOccurrenceException.Status.RESCHEDULED
    exception.version += 1
    exception.save()


def _split_future(item, actor, occurrence_key, fields):
    split_value = _parse_occurrence_key(item, occurrence_key)
    local_date = (
        split_value if item.all_day else split_value.astimezone(ZoneInfo(item.timezone)).date()
    )
    if item.recurrence_frequency == ScheduleItem.RecurrenceFrequency.NONE:
        _apply_fields(item, fields)
        return item
    original_until = item.recurrence_until
    item.recurrence_until = local_date - timedelta(days=1)
    item.version += 1
    item.save()

    new_item = copy(item)
    new_item.pk = None
    new_item.id = None
    new_item.version = 1
    new_item.recurrence_until = original_until
    if item.all_day:
        duration = item.ends_on - item.starts_on
        new_item.starts_on = split_value
        new_item.ends_on = split_value + duration
    else:
        duration = item.ends_at - item.starts_at
        new_item.starts_at = split_value
        new_item.ends_at = split_value + duration
    reminders = _apply_fields(new_item, fields)
    new_item.save()
    source_reminders = reminders
    if source_reminders is None:
        source_reminders = [
            {"offset_minutes": reminder.offset_minutes, "mandatory": reminder.mandatory}
            for reminder in item.reminders.all()
        ]
    _replace_reminders(new_item, source_reminders)
    if item.scope == ScheduleItem.Scope.GROUP:
        for audience in item.audiences.all():
            ScheduleAudience.objects.create(
                schedule_item=new_item,
                scope_type=audience.scope_type,
                project_id=audience.project_id,
                account_id=audience.account_id,
                created_by=actor,
            )
        for grant in item.recipient_grants.filter(valid_until__isnull=True):
            ScheduleRecipientGrant.objects.create(
                schedule_item=new_item,
                recipient_id=grant.recipient_id,
                valid_from=grant.valid_from,
                source_types=grant.source_types,
                source_project_ids=grant.source_project_ids,
            )
    return new_item


@transaction.atomic
def update_schedule(*, item, actor, expected_version, change_scope, fields, occurrence_key=None):
    locked = ScheduleItem.objects.select_for_update().get(pk=item.pk)
    _assert_can_change(actor, locked)
    _assert_version(locked, expected_version)
    fields = dict(fields or {})
    if change_scope == "occurrence":
        exception = _exception_for(locked, occurrence_key, actor)
        _apply_exception_fields(exception, fields)
        locked.version += 1
        locked.save(update_fields=["version", "updated_at"])
        if locked.scope == ScheduleItem.Scope.GROUP:
            _record_group_revision(
                locked,
                actor,
                ScheduleRevision.ChangeType.OCCURRENCE_CHANGED,
                fields.keys(),
                occurrence_key or "",
            )
            from .reminder_services import dispatch_group_event

            dispatch_group_event(locked, actor=actor, event_type="changed")
        return locked
    if change_scope == "future":
        future = _split_future(locked, actor, occurrence_key, fields)
        if locked.scope == ScheduleItem.Scope.GROUP:
            _record_group_revision(
                future,
                actor,
                ScheduleRevision.ChangeType.CHANGED,
                fields.keys(),
                occurrence_key or "",
            )
            from .reminder_services import dispatch_group_event

            dispatch_group_event(future, actor=actor, event_type="changed")
        return future
    if change_scope != "series":
        raise ValidationError({"changeScope": "Choose occurrence, future, or series."})
    reminders = _apply_fields(locked, fields)
    locked.version += 1
    locked.save()
    _replace_reminders(locked, reminders)
    if locked.scope == ScheduleItem.Scope.GROUP:
        _record_group_revision(locked, actor, ScheduleRevision.ChangeType.CHANGED, fields.keys())
        from .reminder_services import dispatch_group_event

        dispatch_group_event(locked, actor=actor, event_type="changed")
    return locked


@transaction.atomic
def cancel_schedule(
    *,
    item,
    actor,
    expected_version,
    change_scope,
    occurrence_key=None,
    reason="",
):
    locked = ScheduleItem.objects.select_for_update().get(pk=item.pk)
    if locked.scope != ScheduleItem.Scope.GROUP:
        raise PermissionDenied("Private schedules must be deleted, not cancelled.")
    _assert_can_change(actor, locked)
    _assert_version(locked, expected_version)
    target = locked
    if change_scope == "occurrence":
        exception = _exception_for(locked, occurrence_key, actor)
        exception.status = ScheduleOccurrenceException.Status.CANCELLED
        exception.version += 1
        exception.save()
        locked.version += 1
        locked.save(update_fields=["version", "updated_at"])
    elif change_scope == "future":
        target = _split_future(locked, actor, occurrence_key, {})
        target.status = ScheduleItem.Status.CANCELLED
        target.cancelled_at = timezone.now()
        target.version += 1
        target.save()
    elif change_scope == "series":
        locked.status = ScheduleItem.Status.CANCELLED
        locked.cancelled_at = timezone.now()
        locked.version += 1
        locked.save()
    else:
        raise ValidationError({"changeScope": "Choose occurrence, future, or series."})
    _record_group_revision(
        target,
        actor,
        ScheduleRevision.ChangeType.CANCELLED,
        ["status", *(["reason"] if reason else [])],
        occurrence_key or "",
    )
    from apps.audit.services import record_schedule_event

    from .reminder_services import dispatch_group_event

    record_schedule_event(
        actor=actor,
        schedule_item=target,
        action="cancelled",
        outcome="success",
        audience={
            "activeRecipientCount": target.recipient_grants.filter(valid_until__isnull=True).count()
        },
    )
    dispatch_group_event(target, actor=actor, event_type="cancelled")
    return target


@transaction.atomic
def complete_schedule(*, item, actor, expected_version, change_scope, occurrence_key=None):
    locked = ScheduleItem.objects.select_for_update().get(pk=item.pk)
    _assert_owner(actor, locked)
    _assert_version(locked, expected_version)
    if change_scope == "occurrence":
        exception = _exception_for(locked, occurrence_key, actor)
        exception.status = ScheduleOccurrenceException.Status.COMPLETED
        exception.version += 1
        exception.save()
    elif change_scope == "future":
        future = _split_future(locked, actor, occurrence_key, {})
        future.status = ScheduleItem.Status.COMPLETED
        future.save()
    elif change_scope == "series":
        locked.status = ScheduleItem.Status.COMPLETED
        locked.version += 1
        locked.save()
    else:
        raise ValidationError({"changeScope": "Choose occurrence, future, or series."})
    if change_scope != "series":
        locked.version += 1
        locked.save(update_fields=["version", "updated_at"])
    return locked


@transaction.atomic
def delete_private_schedule(*, item, actor, expected_version, change_scope, occurrence_key=None):
    locked = ScheduleItem.objects.select_for_update().get(pk=item.pk)
    _assert_owner(actor, locked)
    if locked.scope != ScheduleItem.Scope.PERSONAL:
        raise PermissionDenied("Published schedules must be cancelled, not deleted.")
    _assert_version(locked, expected_version)
    if change_scope == "occurrence":
        exception = _exception_for(locked, occurrence_key, actor)
        exception.status = ScheduleOccurrenceException.Status.CANCELLED
        exception.version += 1
        exception.save()
        locked.version += 1
        locked.save(update_fields=["version", "updated_at"])
    elif change_scope == "future":
        split_value = _parse_occurrence_key(locked, occurrence_key)
        local_date = (
            split_value
            if locked.all_day
            else split_value.astimezone(ZoneInfo(locked.timezone)).date()
        )
        locked.recurrence_until = local_date - timedelta(days=1)
        locked.version += 1
        locked.save()
    elif change_scope == "series":
        locked.delete()
    else:
        raise ValidationError({"changeScope": "Choose occurrence, future, or series."})
