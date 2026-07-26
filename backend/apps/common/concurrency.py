from collections.abc import Callable, Mapping
from typing import Any

from django.db import IntegrityError, transaction


class VersionConflict(Exception):
    def __init__(self, current_state: Mapping[str, Any]):
        super().__init__("The record changed after it was loaded.")
        self.current_state = dict(current_state)


def require_expected_version(
    instance,
    expected_version: int,
    *,
    safe_state: Callable[[Any], Mapping[str, Any]] | None = None,
):
    if instance.version != expected_version:
        snapshot = safe_state(instance) if safe_state else {
            "id": instance.pk,
            "version": instance.version,
        }
        raise VersionConflict(snapshot)
    return instance


@transaction.atomic
def idempotent_mutation(model, *, lookup: Mapping[str, Any], mutation: Callable[[], Any]):
    existing = model.objects.filter(**lookup).first()
    if existing is not None:
        return existing, False
    try:
        with transaction.atomic():
            result = mutation()
    except IntegrityError:
        return model.objects.get(**lookup), False
    return result, True
