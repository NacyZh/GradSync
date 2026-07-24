from rest_framework.exceptions import ValidationError
from rest_framework.pagination import PageNumberPagination


class DefaultPagination(PageNumberPagination):
    page_size = 50
    page_size_query_param = "page_size"
    max_page_size = 200


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
