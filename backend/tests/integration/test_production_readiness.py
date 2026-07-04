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
    assert "proxy_pass http://gradsync_backend/;" not in nginx_conf
    assert "location = /healthz/" in nginx_conf
    assert "location = /readyz/" in nginx_conf
    assert "location = /metrics/" in nginx_conf
    assert "proxy_set_header Host $host;" in nginx_conf
    assert "proxy_set_header X-Forwarded-Proto https;" in nginx_conf
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
    assert "--workers \"$${GRADSYNC_GUNICORN_WORKERS:-1}\"" in compose
    assert "--concurrency=\"$${GRADSYNC_CELERY_CONCURRENCY:-1}\"" in compose
    assert "mem_limit: ${GRADSYNC_BACKEND_MEM_LIMIT:-256m}" in compose
    assert "mem_limit: ${GRADSYNC_WORKER_MEM_LIMIT:-256m}" in compose
    assert "max_connections=${GRADSYNC_POSTGRES_MAX_CONNECTIONS:-40}" in compose
    assert "X-Forwarded-Proto':'https'" in compose
    assert "http://127.0.0.1:8080/healthz/" in compose


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


def test_release_workflow_deploys_by_ssh_with_protected_environment():
    workflow = (REPO_ROOT / ".github/workflows/release.yml").read_text()

    assert "concurrency:" in workflow
    assert "timeout-minutes:" in workflow
    assert "persist-credentials: false" in workflow
    assert "DJANGO_SETTINGS_MODULE: gradsync.settings.ci" in workflow
    assert "GRADSYNC_BACKEND_SETTINGS: ${{ env.DJANGO_SETTINGS_MODULE }}" in workflow
    assert 'OPENAPI_STRICT_SHAPES: "1"' in workflow
    assert "specs/001-research-group-ops/contracts/openapi.yaml" in workflow
    assert "specs/003-research-collab-platform/contracts/openapi.yaml" not in workflow
    assert "production-image:" in workflow
    assert "docker compose -f docker-compose.prod.yml config --quiet" in workflow
    assert "docker build -f docker/backend.Dockerfile" in workflow
    assert "docker build -f docker/frontend.Dockerfile" in workflow
    assert "needs: [backend, frontend, production-image]" in workflow
    assert "Check generated artifacts after frontend build" in workflow
    assert "Run US4 research assets and locale e2e" not in workflow
    assert "Run production UI layout checks" not in workflow
    assert "deploy-production" in workflow
    assert "environment:" in workflow
    assert "PRODUCTION_DEPLOY_SSH_KEY" in workflow
    assert "PRODUCTION_ENV_FILE" in workflow
    assert "GRADSYNC_PRODUCTION_HOST" in workflow
    assert "GRADSYNC_DEPLOY_PATH" in workflow
    assert "scripts/deploy-production.sh" in workflow


def test_deploy_script_fetches_code_and_restarts_stack():
    script = (REPO_ROOT / "scripts/deploy-production.sh").read_text()

    assert "git pull --ff-only" in script
    assert 'docker compose --env-file "$COMPOSE_ENV_FILE" -f "$COMPOSE_FILE"' in script
    assert 'COMPOSE_PARALLEL_LIMIT="${COMPOSE_PARALLEL_LIMIT:-1}"' in script
    assert "compose stop backend frontend worker scheduler" in script
    assert "compose rm -f backend frontend worker scheduler" in script
    assert "docker builder prune -af" in script
    assert "docker image prune -f" in script
    assert "compose build --pull backend" in script
    assert "compose build --pull frontend" in script
    assert "build --pull backend frontend" not in script
    assert "compose run --rm migrate" in script
    assert "compose up -d --no-deps --remove-orphans backend" in script
    assert "compose exec -T backend python manage.py check --deploy" in script
    assert (
        "compose exec -T backend python manage.py check_production_readiness --skip-repo-files"
        in script
    )
    assert "--repo-root /app" not in script
    assert "run --rm backend python manage.py check --deploy" not in script
    assert "drop_caches" not in script
    assert "$PUBLIC_URL/healthz/" in script
    assert "$PUBLIC_URL/readyz/" in script
    assert "$PUBLIC_URL/api/schema/" in script


def test_env_template_names_operational_launch_inputs():
    env_template = (REPO_ROOT / ".env.production.example").read_text()

    for name in [
        "TLS_CERTIFICATE_PATH",
        "TLS_PRIVATE_KEY_PATH",
        "POSTGRES_BACKUP_OFFSITE_URI",
        "BACKUP_RESTORE_DRILL_EVIDENCE",
        "GRADSYNC_POSTGRES_MAX_CONNECTIONS",
        "GRADSYNC_CELERY_CONCURRENCY",
        "GRADSYNC_GUNICORN_WORKERS",
        "GRADSYNC_BACKEND_MEM_LIMIT",
        "GRADSYNC_WORKER_MEM_LIMIT",
        "EMAIL_PROVIDER",
        "EMAIL_DKIM_SELECTOR",
        "ALERT_WEBHOOK_URL",
        "REGISTRY_IMAGE_PREFIX",
        "BACKEND_IMAGE",
        "FRONTEND_IMAGE",
        "DEPLOY_SSH_KEY_SECRET_NAME",
    ]:
        assert name in env_template


def test_production_settings_expose_operational_readiness_env_names():
    production_settings = (REPO_ROOT / "backend/gradsync/settings/production.py").read_text()

    for name in [
        "PUBLIC_BASE_URL",
        "TLS_CERTIFICATE_PATH",
        "TLS_PRIVATE_KEY_PATH",
        "EMAIL_PROVIDER",
        "EMAIL_PROVIDER_DOMAIN",
        "EMAIL_DKIM_SELECTOR",
        "ALERT_WEBHOOK_URL",
        "ALERT_ONCALL_TARGET",
        "REGISTRY_IMAGE_PREFIX",
        "BACKEND_IMAGE",
        "FRONTEND_IMAGE",
        "POSTGRES_BACKUP_OFFSITE_URI",
        "BACKUP_RESTORE_DRILL_EVIDENCE",
    ]:
        assert f'{name} = os.getenv("{name}", "").strip()' in production_settings


def test_restore_drill_script_records_evidence_path():
    script = (REPO_ROOT / "scripts/postgres-restore-drill.sh").read_text()

    assert "BACKUP_RESTORE_DRILL_EVIDENCE" in script
    assert "postgres-restore.sh" in script
    assert "check_production_readiness --skip-database --skip-repo-files" in script


def test_production_readiness_rejects_placeholder_restore_drill(tmp_path):
    evidence = tmp_path / "latest.md"
    evidence.write_text(
        "# Latest Restore Drill Evidence\n\n"
        "Status: pending first production drill\n\n"
        "| Field | Value |\n"
        "|-------|-------|\n"
        "| Backup artifact | Pending |\n"
        "| Off-host storage URI | Pending |\n"
        "| Restore target | Pending |\n"
        "| Started at | Pending |\n"
        "| Completed at | Pending |\n"
        "| Operator | Pending |\n"
        "| RPO result | Pending |\n"
        "| RTO result | Pending |\n"
        "| Validation commands | Pending |\n"
        "| Outcome | Pending |\n"
    )
    settings = production_ready_settings_stub(BACKUP_RESTORE_DRILL_EVIDENCE="latest.md")

    issues = collect_production_readiness_issues(settings, tmp_path)

    assert any("completed restore drill evidence" in issue for issue in issues)


def test_notification_delivery_uses_dedicated_queue():
    from apps.notifications.tasks import deliver_due_notifications_task

    assert deliver_due_notifications_task.queue == "notifications"


def test_production_readiness_flags_configured_sentry_when_not_initialized():
    settings = production_ready_settings_stub(
        SENTRY_DSN="https://example@sentry.test/1", ERROR_REPORTING_ENABLED=False
    )

    issues = collect_production_readiness_issues(settings, REPO_ROOT)

    assert "SENTRY_DSN is configured but error reporting did not initialize" in issues


def test_production_readiness_smtp_probe_uses_delivery_path(settings, tmp_path):
    settings.DEBUG = False
    settings.SECRET_KEY = "x" * 64
    settings.ALLOWED_HOSTS = ["gradsync.example.edu"]
    settings.CSRF_TRUSTED_ORIGINS = ["https://gradsync.example.edu"]
    settings.SESSION_COOKIE_SECURE = True
    settings.CSRF_COOKIE_SECURE = True
    settings.SECURE_HSTS_SECONDS = 31536000
    static_root = tmp_path / "staticfiles"
    static_root.mkdir()
    settings.STATIC_ROOT = str(static_root)
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
