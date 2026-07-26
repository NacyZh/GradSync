from dataclasses import dataclass
from datetime import date

from django.core.exceptions import ValidationError


@dataclass(frozen=True)
class DateRange:
    start: date
    end: date


def bounded_date_range(start, end, *, maximum_days: int = 731) -> DateRange:
    try:
        start_date = start if isinstance(start, date) else date.fromisoformat(str(start))
        end_date = end if isinstance(end, date) else date.fromisoformat(str(end))
    except ValueError as exc:
        raise ValidationError("Date range values must use ISO-8601 dates.") from exc
    if end_date < start_date:
        raise ValidationError("Date range end must not precede start.")
    if (end_date - start_date).days > maximum_days:
        raise ValidationError(f"Date range cannot exceed {maximum_days} days.")
    return DateRange(start=start_date, end=end_date)


def bounded_period_count(value, *, maximum: int = 104) -> int:
    try:
        count = int(value)
    except (TypeError, ValueError) as exc:
        raise ValidationError("Period count must be an integer.") from exc
    if not 1 <= count <= maximum:
        raise ValidationError(f"Period count must be between 1 and {maximum}.")
    return count
