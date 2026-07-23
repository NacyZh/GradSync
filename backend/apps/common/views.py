from django.apps import apps
from django.conf import settings
from django.db import connection
from django.http import HttpResponse, JsonResponse
from django.utils import timezone
from redis import Redis
from drf_spectacular.utils import extend_schema
from rest_framework import serializers
from rest_framework import status
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
    Notification = apps.get_model("notifications", "Notification")
    ResearchProject = apps.get_model("projects", "ResearchProject")
    ScheduleNotificationDispatch = apps.get_model("schedules", "ScheduleNotificationDispatch")

    lines = [
        "# HELP gradsync_projects_total Total GradSync projects.",
        "# TYPE gradsync_projects_total gauge",
        f"gradsync_projects_total {ResearchProject.objects.count()}",
        "# HELP gradsync_notifications_pending Pending notification records.",
        "# TYPE gradsync_notifications_pending gauge",
        f"gradsync_notifications_pending {Notification.objects.filter(status='pending').count()}",
        "# HELP gradsync_schedule_dispatch_total Schedule dispatches by channel and status.",
        "# TYPE gradsync_schedule_dispatch_total gauge",
    ]
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
