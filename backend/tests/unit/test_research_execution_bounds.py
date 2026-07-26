import pytest
from django.core.exceptions import ValidationError
from rest_framework.exceptions import ValidationError as ApiValidationError

from apps.common.pagination import bounded_page_size, parse_bounded_cursor
from apps.common.ranges import bounded_date_range, bounded_period_count


def test_page_size_and_cursor_are_bounded():
    assert parse_bounded_cursor("25", page_size="100").after_id == 25
    with pytest.raises(ApiValidationError):
        bounded_page_size(101)


def test_analytics_and_date_ranges_are_bounded():
    assert bounded_period_count(104) == 104
    with pytest.raises(ValidationError):
        bounded_period_count(105)
    with pytest.raises(ValidationError):
        bounded_date_range("2024-01-01", "2026-01-02", maximum_days=365)
