from importlib import import_module

import pytest
from django.db import connection

from apps.notifications.models import Notification
from apps.submissions.models import ProjectReportSchedule

pytestmark = pytest.mark.django_db


def test_schedule_schema_is_additive_and_report_policy_has_no_implicit_rows():
    tables = set(connection.introspection.table_names())
    assert "schedules_scheduleitem" in tables
    assert "schedules_schedulerecipientgrant" in tables
    assert "schedules_schedulenotificationdispatch" in tables
    assert ProjectReportSchedule.objects.count() == 0
    assert Notification._meta.get_field("delivery_policy").default == "in_app_email"


def test_schedule_migration_operations_are_reversible_and_do_not_rewrite_source_rows():
    schedule_migration = import_module("apps.schedules.migrations.0001_initial").Migration
    report_migration = import_module(
        "apps.submissions.migrations.0006_projectreportschedule"
    ).Migration
    notification_migration = import_module(
        "apps.notifications.migrations.0006_notification_delivery_policy_and_more"
    ).Migration

    operations = [
        *schedule_migration.operations,
        *report_migration.operations,
        *notification_migration.operations,
    ]
    assert all(operation.reversible for operation in operations)
    assert not any(operation.__class__.__name__ == "RunPython" for operation in operations)
