from django.db.models import Q


def apply_text_search(queryset, search: str | None, fields: list[str]):
    if not search:
        return queryset
    query = Q()
    for field in fields:
        query |= Q(**{f"{field}__icontains": search})
    return queryset.filter(query)
