from dataclasses import dataclass

from rest_framework.exceptions import ValidationError
from rest_framework.pagination import PageNumberPagination


class DefaultPagination(PageNumberPagination):
    page_size = 50
    page_size_query_param = "page_size"
    max_page_size = 100


@dataclass(frozen=True)
class CursorPage:
    after_id: int | None
    page_size: int


def bounded_page_size(value, *, default: int = 50, maximum: int = 100) -> int:
    if value in {None, ""}:
        return default
    try:
        page_size = int(value)
    except (TypeError, ValueError) as exc:
        raise ValidationError("Page size must be an integer.") from exc
    if not 1 <= page_size <= maximum:
        raise ValidationError(f"Page size must be between 1 and {maximum}.")
    return page_size


def parse_id_cursor(value: str | None) -> int | None:
    if not value:
        return None
    try:
        cursor = int(value)
    except (TypeError, ValueError) as exc:
        raise ValidationError({"cursor": "Enter a valid audit cursor."}) from exc
    if cursor < 1:
        raise ValidationError({"cursor": "Enter a valid audit cursor."})
    return cursor


def parse_bounded_cursor(value, *, page_size=None, default: int = 50, maximum: int = 100):
    after_id = None
    if value not in {None, ""}:
        try:
            after_id = int(value)
        except (TypeError, ValueError) as exc:
            raise ValidationError({"cursor": "Cursor is invalid."}) from exc
        if after_id < 1:
            raise ValidationError({"cursor": "Cursor is invalid."})
    return CursorPage(
        after_id=after_id,
        page_size=bounded_page_size(page_size, default=default, maximum=maximum),
    )
