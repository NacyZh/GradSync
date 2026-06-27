from pathlib import Path

from django.core import mail
from django.core.management import call_command

from apps.common.production_checks import (
    collect_production_readiness_issues,
    production_ready_settings_stub,
)

REPO_ROOT = Path(__file__).resolve().parents[3]


def test_production_readiness_accepts_secure_settings_and_compose_topology():
    issues = collect_production_readiness_issues(production_ready_settings_stub(), REPO_ROOT)

    assert issues == []


def test_production_readiness_flags_unsafe_settings():
    settings = production_ready_settings_stub(
        DEBUG=True,
        SECRET_KEY="change-me",
        ALLOWED_HOSTS=["*"],
        CSRF_TRUSTED_ORIGINS=[],
        SESSION_COOKIE_SECURE=False,
        CSRF_COOKIE_SECURE=False,
        SECURE_HSTS_SECONDS=0,
    )

    issues = collect_production_readiness_issues(settings, REPO_ROOT)

    assert "DEBUG must be false" in issues
    assert "SECRET_KEY must be non-default" in issues
    assert "ALLOWED_HOSTS must be explicit" in issues
    assert "CSRF_TRUSTED_ORIGINS must be configured" in issues


def test_frontend_nginx_serves_static_assets_and_proxies_api():
    nginx_conf = (REPO_ROOT / "docker/nginx.conf").read_text()

    assert "proxy_pass http://gradsync_backend" in nginx_conf
    assert 'Cache-Control "public, max-age=31536000, immutable"' in nginx_conf
    assert "try_files $uri /index.html" in nginx_conf


def test_production_compose_has_healthchecks_and_no_source_bind_mounts():
    compose = (REPO_ROOT / "docker-compose.prod.yml").read_text()

    assert "healthcheck:" in compose
    assert "condition: service_healthy" in compose
    assert "./backend:" not in compose
    assert "./frontend:" not in compose
    assert "${BACKEND_IMAGE" in compose
    assert "${FRONTEND_IMAGE" in compose


def test_production_operational_docs_are_present_and_actionable():
    required_docs = [
        "docs/ops/credential-inventory.md",
        "docs/ops/infrastructure.md",
        "docs/ops/tls-domain.md",
        "docs/ops/monitoring-alerts.md",
        "docs/ops/email-provider.md",
        "docs/ops/backup-restore-drill.md",
        "docs/ops/cicd-credentials.md",
    ]

    for relative_path in required_docs:
        text = (REPO_ROOT / relative_path).read_text()
        assert "Acceptance" in text or "Validation" in text or "Gate" in text


def test_release_workflow_publishes_images_and_uses_protected_deploy_environment():
    workflow = (REPO_ROOT / ".github/workflows/release.yml").read_text()

    assert "GRADSYNC_REGISTRY_TOKEN" in workflow
    assert "docker push" in workflow
    assert "deploy-production" in workflow
    assert "environment:" in workflow
    assert "PRODUCTION_DEPLOY_SSH_KEY" in workflow
    assert "PRODUCTION_ENV_FILE" in workflow


def test_env_template_names_operational_launch_inputs():
    env_template = (REPO_ROOT / ".env.production.example").read_text()

    for name in [
        "TLS_CERTIFICATE_PATH",
        "TLS_PRIVATE_KEY_PATH",
        "POSTGRES_BACKUP_OFFSITE_URI",
        "BACKUP_RESTORE_DRILL_EVIDENCE",
        "EMAIL_PROVIDER",
        "EMAIL_DKIM_SELECTOR",
        "ALERT_WEBHOOK_URL",
        "REGISTRY_IMAGE_PREFIX",
        "BACKEND_IMAGE",
        "FRONTEND_IMAGE",
        "DEPLOY_SSH_KEY_SECRET_NAME",
    ]:
        assert name in env_template


def test_restore_drill_script_records_evidence_path():
    script = (REPO_ROOT / "scripts/postgres-restore-drill.sh").read_text()

    assert "BACKUP_RESTORE_DRILL_EVIDENCE" in script
    assert "postgres-restore.sh" in script
    assert "check_production_readiness" in script


def test_notification_delivery_uses_dedicated_queue():
    from apps.notifications.tasks import deliver_due_notifications_task

    assert deliver_due_notifications_task.queue == "notifications"


def test_production_readiness_flags_configured_sentry_when_not_initialized():
    settings = production_ready_settings_stub(
        SENTRY_DSN="https://example@sentry.test/1", ERROR_REPORTING_ENABLED=False
    )

    issues = collect_production_readiness_issues(settings, REPO_ROOT)

    assert "SENTRY_DSN is configured but error reporting did not initialize" in issues


def test_production_readiness_smtp_probe_uses_delivery_path(settings):
    settings.DEBUG = False
    settings.SECRET_KEY = "x" * 64
    settings.ALLOWED_HOSTS = ["gradsync.example.edu"]
    settings.CSRF_TRUSTED_ORIGINS = ["https://gradsync.example.edu"]
    settings.SESSION_COOKIE_SECURE = True
    settings.CSRF_COOKIE_SECURE = True
    settings.SECURE_HSTS_SECONDS = 31536000
    settings.STATIC_ROOT = str(REPO_ROOT / "frontend" / "dist")
    settings.EMAIL_HOST = "localhost"
    settings.DEFAULT_FROM_EMAIL = "no-reply@example.edu"
    settings.EMAIL_BACKEND = "django.core.mail.backends.locmem.EmailBackend"
    settings.CELERY_BROKER_URL = "redis://redis:6379/0"
    settings.PUBLIC_BASE_URL = "https://gradsync.edu"
    settings.TLS_CERTIFICATE_PATH = "/etc/letsencrypt/live/gradsync.edu/fullchain.pem"
    settings.TLS_PRIVATE_KEY_PATH = "/etc/letsencrypt/live/gradsync.edu/privkey.pem"
    settings.EMAIL_PROVIDER = "smtp-provider"
    settings.EMAIL_PROVIDER_DOMAIN = "gradsync.edu"
    settings.EMAIL_DKIM_SELECTOR = "gradsync"
    settings.ALERT_WEBHOOK_URL = "https://alerts.gradsync.edu/hooks/grad-sync"
    settings.ALERT_ONCALL_TARGET = "grad-sync-primary"
    settings.REGISTRY_IMAGE_PREFIX = "ghcr.io/gradsync-prod/gradsync"
    settings.BACKEND_IMAGE = "ghcr.io/gradsync-prod/gradsync/backend:abc123"
    settings.FRONTEND_IMAGE = "ghcr.io/gradsync-prod/gradsync/frontend:abc123"
    settings.POSTGRES_BACKUP_OFFSITE_URI = "s3://gradsync-prod-backups/postgres/"
    settings.BACKUP_RESTORE_DRILL_EVIDENCE = "docs/ops/restore-drills/latest.md"

    call_command(
        "check_production_readiness",
        repo_root=str(REPO_ROOT),
        skip_database=True,
        smtp_probe_to="ops@example.edu",
    )

    assert len(mail.outbox) == 1
    assert mail.outbox[0].to == ["ops@example.edu"]
