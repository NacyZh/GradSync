import pytest


@pytest.fixture
def api_client():
    from rest_framework.test import APIClient

    return APIClient()


@pytest.fixture
def schedule_factory():
    from tests.factories.schedules import ScheduleItemFactory

    return ScheduleItemFactory
