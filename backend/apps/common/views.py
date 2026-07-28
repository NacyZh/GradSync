from django.apps import apps
from django.conf import settings
from django.db import connection
from django.db.models import Q
from django.http import HttpResponse, JsonResponse
from django.utils import timezone
from drf_spectacular.utils import extend_schema
from redis import Redis
from rest_framework import serializers, status
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from .upload_policy import UploadCategory, configured_upload_policy


class UploadPolicyResponseSerializer(serializers.Serializer):
    category = serializers.ChoiceField(choices=[item.value for item in UploadCategory])
    maxSizeBytes = serializers.IntegerField(min_value=1)
    displayLabel = serializers.CharField()
    allowedExtensions = serializers.ListField(child=serializers.CharField())
    contentTypes = serializers.ListField(child=serializers.CharField())


def healthz(_request):
    return JsonResponse({"status": "ok"})


def readyz(_request):
    checks = {"database": False, "redis": False}
    status = 200
    try:
        with connection.cursor() as cursor:
            cursor.execute("SELECT 1")
            checks["database"] = cursor.fetchone()[0] == 1
    except Exception:
        status = 503

    try:
        checks["redis"] = Redis.from_url(
            settings.CELERY_BROKER_URL, socket_connect_timeout=1
        ).ping()
    except Exception:
        status = 503

    return JsonResponse(
        {"status": "ok" if status == 200 else "unavailable", "checks": checks}, status=status
    )


def metrics(_request):
    AccountRecoveryRequest = apps.get_model("accounts", "AccountRecoveryRequest")
    AccountSession = apps.get_model("accounts", "AccountSession")
    AuditExport = apps.get_model("audit", "AuditExport")
    Notification = apps.get_model("notifications", "Notification")
    NotificationDeliveryAttempt = apps.get_model("notifications", "NotificationDeliveryAttempt")
    ResearchProject = apps.get_model("projects", "ResearchProject")
    RiskRecord = apps.get_model("projects", "RiskRecord")
    ReportingPeriod = apps.get_model("submissions", "ReportingPeriod")
    WeeklyProgressReport = apps.get_model("submissions", "WeeklyProgressReport")
    ScheduleNotificationDispatch = apps.get_model("schedules", "ScheduleNotificationDispatch")
    pending_recoveries = AccountRecoveryRequest.objects.filter(status="pending").count()
    revoked_sessions = AccountSession.objects.filter(status="revoked").count()
    oldest_export = (
        AuditExport.objects.filter(status__in=["queued", "processing"])
        .order_by("created_at")
        .first()
    )
    export_queue_age = (
        max(0, int((timezone.now() - oldest_export.created_at).total_seconds()))
        if oldest_export
        else 0
    )
    actionable_risks = (
        RiskRecord.objects.filter(state__in=["raised", "open", "mitigating"])
        .filter(Q(severity="high") | Q(review_date__lt=timezone.localdate()))
        .count()
    )

    lines = [
        "# HELP gradsync_projects_total Total GradSync projects.",
        "# TYPE gradsync_projects_total gauge",
        f"gradsync_projects_total {ResearchProject.objects.count()}",
        "# HELP gradsync_reporting_periods_open Open structured reporting periods.",
        "# TYPE gradsync_reporting_periods_open gauge",
        (f"gradsync_reporting_periods_open {ReportingPeriod.objects.filter(state='open').count()}"),
        "# HELP gradsync_structured_reports_unlinked Legacy reports awaiting backfill.",
        "# TYPE gradsync_structured_reports_unlinked gauge",
        (
            "gradsync_structured_reports_unlinked "
            f"{WeeklyProgressReport.objects.filter(reporting_period__isnull=True).count()}"
        ),
        "# HELP gradsync_risks_actionable Open high or overdue risks.",
        "# TYPE gradsync_risks_actionable gauge",
        f"gradsync_risks_actionable {actionable_risks}",
        "# HELP gradsync_notifications_pending Pending notification records.",
        "# TYPE gradsync_notifications_pending gauge",
        f"gradsync_notifications_pending {Notification.objects.filter(status='pending').count()}",
        "# HELP gradsync_notification_followups_total Actionable notifications by outcome.",
        "# TYPE gradsync_notification_followups_total gauge",
        (
            "# HELP gradsync_notification_delivery_attempts_total "
            "Delivery attempts by channel and state."
        ),
        "# TYPE gradsync_notification_delivery_attempts_total gauge",
        "# HELP gradsync_account_recovery_pending Pending account recovery requests.",
        "# TYPE gradsync_account_recovery_pending gauge",
        f"gradsync_account_recovery_pending {pending_recoveries}",
        "# HELP gradsync_account_sessions_revoked Revoked authoritative account sessions.",
        "# TYPE gradsync_account_sessions_revoked gauge",
        f"gradsync_account_sessions_revoked {revoked_sessions}",
        "# HELP gradsync_audit_exports_pending Queued or processing audit exports.",
        "# TYPE gradsync_audit_exports_pending gauge",
        (
            "gradsync_audit_exports_pending "
            f"{AuditExport.objects.filter(status__in=['queued', 'processing']).count()}"
        ),
        "# HELP gradsync_audit_export_queue_age_seconds Age of oldest pending audit export.",
        "# TYPE gradsync_audit_export_queue_age_seconds gauge",
        f"gradsync_audit_export_queue_age_seconds {export_queue_age}",
        "# HELP gradsync_audit_exports_failed Failed audit exports.",
        "# TYPE gradsync_audit_exports_failed gauge",
        f"gradsync_audit_exports_failed {AuditExport.objects.filter(status='failed').count()}",
        "# HELP gradsync_schedule_dispatch_total Schedule dispatches by channel and status.",
        "# TYPE gradsync_schedule_dispatch_total gauge",
    ]
    for outcome in ("pending", "acknowledged", "completed", "expired", "unavailable"):
        lines.append(
            "gradsync_notification_followups_total"
            f'{{outcome="{outcome}"}} '
            f"{Notification.objects.filter(outcome_state=outcome).count()}"
        )
    for channel in ("in_app", "email"):
        for attempt_state in ("pending", "queued", "sent", "failed", "skipped"):
            attempt_count = NotificationDeliveryAttempt.objects.filter(
                channel=channel, state=attempt_state
            ).count()
            lines.append(
                "gradsync_notification_delivery_attempts_total"
                f'{{channel="{channel}",state="{attempt_state}"}} '
                f"{attempt_count}"
            )
    oldest_attempt = (
        NotificationDeliveryAttempt.objects.filter(state__in=["pending", "queued"])
        .order_by("eligible_at")
        .first()
    )
    notification_lag = (
        max(0, int((timezone.now() - oldest_attempt.eligible_at).total_seconds()))
        if oldest_attempt and oldest_attempt.eligible_at <= timezone.now()
        else 0
    )
    lines.extend(
        [
            "# HELP gradsync_notification_delivery_lag_seconds Age of oldest due attempt.",
            "# TYPE gradsync_notification_delivery_lag_seconds gauge",
            f"gradsync_notification_delivery_lag_seconds {notification_lag}",
        ]
    )
    oldest_claim = (
        ScheduleNotificationDispatch.objects.filter(status="claimed").order_by("created_at").first()
    )
    lag_seconds = (
        max(0, int((timezone.now() - oldest_claim.created_at).total_seconds()))
        if oldest_claim
        else 0
    )
    lines.extend(
        [
            "# HELP gradsync_schedule_dispatch_lag_seconds Age of oldest claimed dispatch.",
            "# TYPE gradsync_schedule_dispatch_lag_seconds gauge",
            f"gradsync_schedule_dispatch_lag_seconds {lag_seconds}",
        ]
    )
    for channel in ("in_app", "email"):
        for dispatch_status in ("claimed", "created", "skipped", "failed"):
            count = ScheduleNotificationDispatch.objects.filter(
                channel=channel, status=dispatch_status
            ).count()
            lines.append(
                "gradsync_schedule_dispatch_total"
                f'{{channel="{channel}",status="{dispatch_status}"}} {count}'
            )
    return HttpResponse("\n".join(lines) + "\n", content_type="text/plain; version=0.0.4")


class UploadPolicyView(APIView):
    permission_classes = [IsAuthenticated]

    @extend_schema(responses=UploadPolicyResponseSerializer)
    def get(self, _request, category: str):
        try:
            policy = configured_upload_policy(UploadCategory(category))
        except ValueError:
            return Response(
                {"message": "Unknown upload category."},
                status=status.HTTP_404_NOT_FOUND,
            )
        return Response(policy)
