from django.conf import settings
from django.db import connection
from django.http import HttpResponse, JsonResponse
from redis import Redis


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
    from apps.notifications.models import Notification
    from apps.projects.models import ResearchProject

    lines = [
        "# HELP gradsync_projects_total Total GradSync projects.",
        "# TYPE gradsync_projects_total gauge",
        f"gradsync_projects_total {ResearchProject.objects.count()}",
        "# HELP gradsync_notifications_pending Pending notification records.",
        "# TYPE gradsync_notifications_pending gauge",
        f"gradsync_notifications_pending {Notification.objects.filter(status='pending').count()}",
    ]
    return HttpResponse("\n".join(lines) + "\n", content_type="text/plain; version=0.0.4")
