import base64
import json

from django.db.models import Q

from .models import ScheduleItem


def encode_event_cursor(updated_at, object_id: int) -> str:
    payload = json.dumps([updated_at.isoformat(), object_id], separators=(",", ":"))
    return base64.urlsafe_b64encode(payload.encode()).decode().rstrip("=")


def decode_event_cursor(cursor: str):
    try:
        raw = base64.urlsafe_b64decode(cursor + "=" * (-len(cursor) % 4))
        value = json.loads(raw)
        return value[0], int(value[1])
    except (ValueError, TypeError, json.JSONDecodeError) as exc:
        raise ValueError("Invalid calendar event cursor.") from exc


def schedule_events_visible_to(user, *, after=None, limit=100):
    visibility = Q(owner=user) | Q(
        scope=ScheduleItem.Scope.GROUP,
        recipient_grants__recipient=user,
        recipient_grants__valid_until__isnull=True,
    )
    if getattr(user, "is_administrator", False):
        visibility |= Q(scope=ScheduleItem.Scope.GROUP)
    queryset = ScheduleItem.objects.filter(visibility).distinct().order_by("updated_at", "id")
    if after:
        updated_at, object_id = decode_event_cursor(after)
        queryset = queryset.filter(
            Q(updated_at__gt=updated_at) | Q(updated_at=updated_at, id__gt=object_id)
        )
    return [
        {
            "cursor": encode_event_cursor(item.updated_at, item.id),
            "type": "schedule.changed",
            "itemId": item.id,
            "updatedAt": item.updated_at,
        }
        for item in queryset[:limit]
    ]
