from datetime import datetime

from django.utils import timezone

from .projection_services import aggregate_calendar_occurrences


def visible_conflicts(
    user, *, starts_at=None, ends_at=None, starts_on=None, ends_on=None, exclude_schedule_id=None
):
    if starts_on:
        window_start = timezone.make_aware(datetime.combine(starts_on, datetime.min.time()))
        window_end = timezone.make_aware(datetime.combine(ends_on, datetime.min.time()))
    else:
        window_start, window_end = starts_at, ends_at
    results = []
    for occurrence in aggregate_calendar_occurrences(user, window_start, window_end):
        if exclude_schedule_id and occurrence.get("scheduleId") == exclude_schedule_id:
            continue
        occurrence_start = occurrence.get("startsAt") or timezone.make_aware(
            datetime.combine(occurrence["startsOn"], datetime.min.time())
        )
        occurrence_end = occurrence.get("endsAt") or timezone.make_aware(
            datetime.combine(occurrence["endsOn"], datetime.min.time())
        )
        if occurrence_start < window_end and occurrence_end > window_start:
            results.append(
                {
                    "occurrenceId": occurrence["occurrenceId"],
                    "title": occurrence["title"],
                    "allDay": occurrence["allDay"],
                    "startsAt": occurrence.get("startsAt"),
                    "endsAt": occurrence.get("endsAt"),
                    "startsOn": occurrence.get("startsOn"),
                    "endsOn": occurrence.get("endsOn"),
                    "scope": occurrence["scope"],
                }
            )
    return results[:20]
