from dataclasses import dataclass
from datetime import date, datetime
from zoneinfo import ZoneInfo

from dateutil.relativedelta import relativedelta
from dateutil.rrule import DAILY, MONTHLY, WEEKLY, rrule

MAX_OCCURRENCES = 1000


class RecurrenceLimitError(ValueError):
    pass


@dataclass(frozen=True)
class ExpandedOccurrence:
    starts_at: datetime | None = None
    ends_at: datetime | None = None
    starts_on: date | None = None
    ends_on: date | None = None


def expand_occurrences(
    *,
    timezone_name: str,
    frequency: str,
    interval: int,
    until: date | None,
    window_start: date | datetime,
    window_end: date | datetime,
    starts_at: datetime | None = None,
    ends_at: datetime | None = None,
    starts_on: date | None = None,
    ends_on: date | None = None,
    weekdays: list[int] | None = None,
) -> list[ExpandedOccurrence]:
    """Expand one bounded series while preserving its configured local wall time."""
    zone = ZoneInfo(timezone_name)
    all_day = starts_on is not None
    first_date = starts_on if all_day else starts_at.astimezone(zone).date()
    if frequency != "none":
        if until is None:
            raise RecurrenceLimitError("Recurring schedules require an end date.")
        if until > first_date + relativedelta(years=2):
            raise RecurrenceLimitError("Recurrence cannot span more than two years.")

    if all_day:
        duration = ends_on - starts_on
        local_start = datetime.combine(starts_on, datetime.min.time(), tzinfo=zone)
    else:
        if starts_at is None or ends_at is None:
            raise ValueError("Timed occurrences require start and end timestamps.")
        local_start = starts_at.astimezone(zone)
        duration = ends_at - starts_at

    dates = _series_dates(local_start, frequency, interval, until, weekdays or [])
    if len(dates) > MAX_OCCURRENCES:
        raise RecurrenceLimitError("A series cannot generate more than 1,000 occurrences.")

    output = []
    for generated in dates:
        if all_day:
            occurrence_start = generated.date()
            occurrence_end = occurrence_start + duration
            if _date_overlaps(occurrence_start, occurrence_end, window_start, window_end):
                output.append(
                    ExpandedOccurrence(starts_on=occurrence_start, ends_on=occurrence_end)
                )
        else:
            occurrence_start = generated.astimezone(ZoneInfo("UTC"))
            occurrence_end = occurrence_start + duration
            if _time_overlaps(occurrence_start, occurrence_end, window_start, window_end, zone):
                output.append(
                    ExpandedOccurrence(starts_at=occurrence_start, ends_at=occurrence_end)
                )
    return output


def _series_dates(start, frequency, interval, until, weekdays):
    if frequency == "none":
        return [start]
    frequency_map = {"daily": DAILY, "weekly": WEEKLY, "monthly": MONTHLY}
    if frequency not in frequency_map:
        raise ValueError("Unsupported recurrence frequency.")
    rule_kwargs = {
        "freq": frequency_map[frequency],
        "dtstart": start,
        "interval": interval,
        "until": datetime.combine(until, datetime.max.time(), tzinfo=start.tzinfo),
    }
    if frequency == "weekly" and weekdays:
        rule_kwargs["byweekday"] = [day - 1 for day in weekdays]
    return list(rrule(**rule_kwargs))


def _date_overlaps(start, end, window_start, window_end):
    window_start_date = window_start.date() if isinstance(window_start, datetime) else window_start
    window_end_date = window_end.date() if isinstance(window_end, datetime) else window_end
    return start < window_end_date and end > window_start_date


def _time_overlaps(start, end, window_start, window_end, zone):
    if not isinstance(window_start, datetime):
        window_start = datetime.combine(window_start, datetime.min.time(), tzinfo=zone)
    if not isinstance(window_end, datetime):
        window_end = datetime.combine(window_end, datetime.min.time(), tzinfo=zone)
    return start < window_end.astimezone(ZoneInfo("UTC")) and end > window_start.astimezone(
        ZoneInfo("UTC")
    )
