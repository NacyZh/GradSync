from datetime import UTC, datetime, timedelta
from pathlib import Path
from types import SimpleNamespace

REQUIRED_OPERATIONAL_DOCS = (
    "docs/ops/credential-inventory.md",
    "docs/ops/infrastructure.md",
    "docs/ops/tls-domain.md",
    "docs/ops/monitoring-alerts.md",
    "docs/ops/email-provider.md",
    "docs/ops/backup-restore-drill.md",
    "docs/ops/cicd-credentials.md",
)


def _has_placeholder(value: str) -> bool:
    lowered = value.lower()
    return not value or "replace-with" in lowered or "example" in lowered


def _table_value(markdown: str, field: str) -> str:
    prefix = f"| {field} |"
    for line in markdown.splitlines():
        if line.startswith(prefix):
            parts = [part.strip() for part in line.strip("|").split("|")]
            return parts[1] if len(parts) > 1 else ""
    return ""


def _validate_restore_drill_evidence(repo_root: Path, relative_path: str) -> list[str]:
    issues: list[str] = []
    evidence_path = repo_root / relative_path
    if not evidence_path.exists():
        return [f"{relative_path} is missing"]
    text = evidence_path.read_text()
    lowered = text.lower()
    if "pending" in lowered or "placeholder" in lowered:
        issues.append(f"{relative_path} must contain completed restore drill evidence")
    for field in (
        "Backup artifact",
        "Off-host storage URI",
        "Restore target",
        "Started at",
        "Completed at",
        "Operator",
        "RPO result",
        "RTO result",
        "Validation commands",
        "Outcome",
    ):
        value = _table_value(text, field)
        if _has_placeholder(value) or value.lower() in {"pending", "recorded by operator"}:
            issues.append(f"{relative_path} field '{field}' must be non-placeholder")
    completed_at = _table_value(text, "Completed at")
    try:
        completed = datetime.fromisoformat(completed_at.replace("Z", "+00:00"))
    except ValueError:
        issues.append(f"{relative_path} Completed at must be ISO-8601")
    else:
        if completed < datetime.now(UTC) - timedelta(days=120):
            issues.append(f"{relative_path} restore drill evidence is older than 120 days")
    if "passed" not in _table_value(text, "Outcome").lower():
        issues.append(f"{relative_path} Outcome must record a passed restore validation")
    return issues


def collect_production_readiness_issues(settings_obj, repo_root: Path | None = None) -> list[str]:
    issues: list[str] = []
    if getattr(settings_obj, "DEBUG", True):
        issues.append("DEBUG must be false")
    if getattr(settings_obj, "SECRET_KEY", "") in {"", "dev-secret-key", "change-me"}:
        issues.append("SECRET_KEY must be non-default")
    if not getattr(settings_obj, "ALLOWED_HOSTS", []) or "*" in getattr(
        settings_obj, "ALLOWED_HOSTS", []
    ):
        issues.append("ALLOWED_HOSTS must be explicit")
    if not getattr(settings_obj, "CSRF_TRUSTED_ORIGINS", []):
        issues.append("CSRF_TRUSTED_ORIGINS must be configured")
    if not getattr(settings_obj, "SESSION_COOKIE_SECURE", False):
        issues.append("SESSION_COOKIE_SECURE must be true")
    if not getattr(settings_obj, "CSRF_COOKIE_SECURE", False):
        issues.append("CSRF_COOKIE_SECURE must be true")
    if getattr(settings_obj, "SECURE_HSTS_SECONDS", 0) <= 0:
        issues.append("SECURE_HSTS_SECONDS must be positive")
    if not getattr(settings_obj, "STATIC_ROOT", None):
        issues.append("STATIC_ROOT must be configured")
    if not getattr(settings_obj, "EMAIL_HOST", ""):
        issues.append("EMAIL_HOST must be configured")
    if not getattr(settings_obj, "DEFAULT_FROM_EMAIL", ""):
        issues.append("DEFAULT_FROM_EMAIL must be configured")
    if not getattr(settings_obj, "CELERY_BROKER_URL", ""):
        issues.append("CELERY_BROKER_URL must be configured")
    notification_queue = getattr(settings_obj, "CELERY_NOTIFICATION_QUEUE", "")
    if _has_placeholder(str(notification_queue)):
        issues.append("CELERY_NOTIFICATION_QUEUE must be configured")
    notification_route = getattr(settings_obj, "CELERY_TASK_ROUTES", {}).get(
        "apps.notifications.tasks.*", {}
    )
    if notification_route.get("queue") != notification_queue:
        issues.append("Notification tasks must route to CELERY_NOTIFICATION_QUEUE")
    if getattr(settings_obj, "SENTRY_DSN", "") and not getattr(
        settings_obj, "ERROR_REPORTING_ENABLED", False
    ):
        issues.append("SENTRY_DSN is configured but error reporting did not initialize")
    for env_name in (
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
    ):
        value = getattr(settings_obj, env_name, "")
        if _has_placeholder(str(value)):
            issues.append(f"{env_name} must be configured with a non-placeholder production value")

    if repo_root is not None:
        compose = repo_root / "docker-compose.prod.yml"
        if not compose.exists():
            issues.append("docker-compose.prod.yml is missing")
        else:
            compose_text = compose.read_text()
            for service in ("backend", "frontend", "db", "redis", "worker", "scheduler"):
                if service not in compose_text:
                    issues.append(f"{service} service is missing from production compose")
            if "healthcheck:" not in compose_text:
                issues.append("production compose healthchecks are missing")
            if "./backend:" in compose_text or "./frontend:" in compose_text:
                issues.append("production compose must not use source bind mounts")
            if "${BACKEND_IMAGE" not in compose_text or "${FRONTEND_IMAGE" not in compose_text:
                issues.append(
                    "production compose must support registry-published backend and frontend images"
                )
        for relative_doc in REQUIRED_OPERATIONAL_DOCS:
            if not (repo_root / relative_doc).exists():
                issues.append(f"{relative_doc} is missing")
        evidence_relative = getattr(
            settings_obj, "BACKUP_RESTORE_DRILL_EVIDENCE", "docs/ops/restore-drills/latest.md"
        )
        issues.extend(_validate_restore_drill_evidence(repo_root, evidence_relative))
        release_workflow = repo_root / ".github/workflows/release.yml"
        if release_workflow.exists():
            workflow_text = release_workflow.read_text()
            for required in (
                "PRODUCTION_DEPLOY_SSH_KEY",
                "PRODUCTION_ENV_FILE",
                "GRADSYNC_PRODUCTION_HOST",
                "GRADSYNC_DEPLOY_PATH",
                "environment:",
                "deploy-production",
                "scripts/deploy-production.sh",
            ):
                if required not in workflow_text:
                    issues.append(f"release workflow is missing {required}")
        else:
            issues.append(".github/workflows/release.yml is missing")
        deploy_script = repo_root / "scripts/deploy-production.sh"
        if not deploy_script.exists():
            issues.append("scripts/deploy-production.sh is missing")
        else:
            deploy_text = deploy_script.read_text()
            for required in (
                "git pull --ff-only",
                "docker compose",
                "python manage.py check --deploy",
                "/healthz/",
                "/readyz/",
                "/api/schema/",
            ):
                if required not in deploy_text:
                    issues.append(f"deploy script is missing {required}")
    return issues


def production_ready_settings_stub(**overrides):
    defaults = {
        "DEBUG": False,
        "SECRET_KEY": "x" * 64,
        "ALLOWED_HOSTS": ["gradsync.example.edu"],
        "CSRF_TRUSTED_ORIGINS": ["https://gradsync.example.edu"],
        "SESSION_COOKIE_SECURE": True,
        "CSRF_COOKIE_SECURE": True,
        "SECURE_HSTS_SECONDS": 31536000,
        "STATIC_ROOT": "/app/backend/staticfiles",
        "EMAIL_HOST": "smtp.example.edu",
        "DEFAULT_FROM_EMAIL": "no-reply@example.edu",
        "CELERY_BROKER_URL": "redis://redis:6379/0",
        "CELERY_NOTIFICATION_QUEUE": "notifications",
        "CELERY_TASK_ROUTES": {"apps.notifications.tasks.*": {"queue": "notifications"}},
        "PUBLIC_BASE_URL": "https://gradsync.edu",
        "TLS_CERTIFICATE_PATH": "/etc/letsencrypt/live/gradsync.edu/fullchain.pem",
        "TLS_PRIVATE_KEY_PATH": "/etc/letsencrypt/live/gradsync.edu/privkey.pem",
        "EMAIL_PROVIDER": "smtp-provider",
        "EMAIL_PROVIDER_DOMAIN": "gradsync.edu",
        "EMAIL_DKIM_SELECTOR": "gradsync",
        "ALERT_WEBHOOK_URL": "https://alerts.gradsync.edu/hooks/grad-sync",
        "ALERT_ONCALL_TARGET": "grad-sync-primary",
        "REGISTRY_IMAGE_PREFIX": "ghcr.io/gradsync-prod/gradsync",
        "BACKEND_IMAGE": "ghcr.io/gradsync-prod/gradsync/backend:abc123",
        "FRONTEND_IMAGE": "ghcr.io/gradsync-prod/gradsync/frontend:abc123",
        "POSTGRES_BACKUP_OFFSITE_URI": "s3://gradsync-prod-backups/postgres/",
        "BACKUP_RESTORE_DRILL_EVIDENCE": "docs/ops/restore-drills/latest.md",
    }
    defaults.update(overrides)
    return SimpleNamespace(**defaults)
