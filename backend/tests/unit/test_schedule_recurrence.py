from datetime import date, datetime, timedelta
from zoneinfo import ZoneInfo

import pytest

from apps.schedules.recurrence import RecurrenceLimitError, expand_occurrences


def test_daily_timed_recurrence_preserves_local_time_across_dst():
    timezone = ZoneInfo("America/New_York")
    starts_at = datetime(2026, 3, 7, 9, tzinfo=timezone)
    occurrences = expand_occurrences(
        starts_at=starts_at,
        ends_at=starts_at + timedelta(hours=1),
        timezone_name="America/New_York",
        frequency="daily",
        interval=1,
        until=date(2026, 3, 9),
        window_start=datetime(2026, 3, 7, tzinfo=ZoneInfo("UTC")),
        window_end=datetime(2026, 3, 11, tzinfo=ZoneInfo("UTC")),
    )

    assert [item.starts_at.astimezone(timezone).hour for item in occurrences] == [9, 9, 9]


def test_monthly_recurrence_uses_month_end_semantics():
    occurrences = expand_occurrences(
        starts_on=date(2026, 1, 31),
        ends_on=date(2026, 2, 1),
        timezone_name="UTC",
        frequency="monthly",
        interval=1,
        until=date(2026, 4, 30),
        window_start=date(2026, 1, 1),
        window_end=date(2026, 5, 1),
    )

    assert [item.starts_on for item in occurrences] == [date(2026, 1, 31), date(2026, 3, 31)]
    assert all(item.ends_on == item.starts_on + timedelta(days=1) for item in occurrences)


def test_recurrence_rejects_more_than_two_years_or_one_thousand_occurrences():
    with pytest.raises(RecurrenceLimitError):
        expand_occurrences(
            starts_on=date(2026, 1, 1),
            ends_on=date(2026, 1, 2),
            timezone_name="UTC",
            frequency="daily",
            interval=1,
            until=date(2028, 1, 2),
            window_start=date(2026, 1, 1),
            window_end=date(2028, 1, 3),
        )
