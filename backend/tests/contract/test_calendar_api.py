from datetime import timedelta

import pytest
from django.utils import timezone

from tests.factories.accounts import UserFactory
from tests.helpers import authenticate

pytestmark = pytest.mark.django_db


def test_calendar_occurrences_require_auth_and_bound_period(api_client):
    now = timezone.now()
    assert api_client.get("/api/calendar/occurrences/").status_code in {401, 403}

    user = UserFactory()
    response = authenticate(api_client, user).get(
        "/api/calendar/occurrences/",
        {"startsAt": now.isoformat(), "endsAt": (now + timedelta(days=63)).isoformat()},
    )
    assert response.status_code == 400
    assert "endsAt" in response.json()


def test_calendar_occurrence_page_and_source_filter_contract(api_client):
    user = UserFactory()
    now = timezone.now()
    response = authenticate(api_client, user).get(
        "/api/calendar/occurrences/",
        {
            "startsAt": now.isoformat(),
            "endsAt": (now + timedelta(days=30)).isoformat(),
            "sources": "task,booking",
        },
    )

    assert response.status_code == 200
    payload = response.json()
    assert set(payload) >= {"results", "generatedAt", "latestEventId", "nextCursor"}
    assert all(item["sourceType"] in {"task", "booking"} for item in payload["results"])


def test_calendar_events_return_safe_opaque_cursor(api_client):
    user = UserFactory()
    response = authenticate(api_client, user).get("/api/calendar/events/")

    assert response.status_code == 200
    assert set(response.json()) >= {"results", "latestEventId", "generatedAt"}
