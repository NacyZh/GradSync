from datetime import UTC, datetime, timedelta
from pathlib import Path
from types import SimpleNamespace
from urllib.parse import urlparse

from django.core.exceptions import ValidationError
from django.core.validators import validate_email

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
    email_host = str(getattr(settings_obj, "EMAIL_HOST", ""))
    default_from_email = str(getattr(settings_obj, "DEFAULT_FROM_EMAIL", ""))
    if _has_placeholder(email_host):
        issues.append("EMAIL_HOST must be configured with a non-placeholder production value")
    if _has_placeholder(default_from_email):
        issues.append(
            "DEFAULT_FROM_EMAIL must be configured with a non-placeholder production value"
        )
    email_port = getattr(settings_obj, "EMAIL_PORT", 0)
    if not isinstance(email_port, int) or not 1 <= email_port <= 65535:
        issues.append("EMAIL_PORT must be between 1 and 65535")
    if getattr(settings_obj, "EMAIL_USE_TLS", False) and getattr(
        settings_obj, "EMAIL_USE_SSL", False
    ):
        issues.append("EMAIL_USE_TLS and EMAIL_USE_SSL cannot both be true")
    if getattr(settings_obj, "EMAIL_TIMEOUT", 0) <= 0:
        issues.append("EMAIL_TIMEOUT must be positive")
    email_user = str(getattr(settings_obj, "EMAIL_HOST_USER", ""))
    email_password = str(getattr(settings_obj, "EMAIL_HOST_PASSWORD", ""))
    if bool(email_user) != bool(email_password):
        issues.append("EMAIL_HOST_USER and EMAIL_HOST_PASSWORD must be configured together")
    if (email_user and _has_placeholder(email_user)) or (
        email_password and _has_placeholder(email_password)
    ):
        issues.append("SMTP credentials must not contain placeholder values")
    smtp_probe_to = str(getattr(settings_obj, "PRODUCTION_SMTP_PROBE_TO", "")).strip()
    if not smtp_probe_to:
        issues.append("PRODUCTION_SMTP_PROBE_TO must configure a dedicated test mailbox")
    else:
        try:
            validate_email(smtp_probe_to)
        except ValidationError:
            issues.append("PRODUCTION_SMTP_PROBE_TO must be a valid email address")
        if smtp_probe_to.casefold() == default_from_email.strip().casefold():
            issues.append("PRODUCTION_SMTP_PROBE_TO must differ from DEFAULT_FROM_EMAIL")
    if not getattr(settings_obj, "CELERY_BROKER_URL", ""):
        issues.append("CELERY_BROKER_URL must be configured")
    approved_origin = str(getattr(settings_obj, "APPROVED_FRONTEND_ORIGIN", "https://localhost"))
    parsed_origin = urlparse(approved_origin)
    if (
        parsed_origin.scheme != "https"
        or not parsed_origin.netloc
        or parsed_origin.path
        not in {
            "",
            "/",
        }
    ):
        issues.append("APPROVED_FRONTEND_ORIGIN must be an HTTPS origin without a path")
    if getattr(settings_obj, "ACCOUNT_RECOVERY_TOKEN_TTL_SECONDS", 1800) > 1800:
        issues.append("ACCOUNT_RECOVERY_TOKEN_TTL_SECONDS cannot exceed 1800")
    if getattr(settings_obj, "EMAIL_CHANGE_TOKEN_TTL_SECONDS", 1800) > 1800:
        issues.append("EMAIL_CHANGE_TOKEN_TTL_SECONDS cannot exceed 1800")
    if getattr(settings_obj, "AUDIT_RETENTION_DAYS", 365) < 365:
        issues.append("AUDIT_RETENTION_DAYS cannot be below 365")
    audit_export_limit = getattr(settings_obj, "AUDIT_EXPORT_MAX_ROWS", 10000)
    if not 1 <= audit_export_limit <= 10000:
        issues.append("AUDIT_EXPORT_MAX_ROWS must be between 1 and 10000")
    notification_queue = getattr(settings_obj, "CELERY_NOTIFICATION_QUEUE", "")
    if _has_placeholder(str(notification_queue)):
        issues.append("CELERY_NOTIFICATION_QUEUE must be configured")
    notification_route = getattr(settings_obj, "CELERY_TASK_ROUTES", {}).get(
        "apps.notifications.tasks.*", {}
    )
    if notification_route.get("queue") != notification_queue:
        issues.append("Notification tasks must route to CELERY_NOTIFICATION_QUEUE")
    threshold_min = getattr(settings_obj, "GRADSYNC_NOTIFICATION_THRESHOLD_MIN_MINUTES", 60)
    threshold_max = getattr(settings_obj, "GRADSYNC_NOTIFICATION_THRESHOLD_MAX_MINUTES", 10080)
    if not 1 <= threshold_min < threshold_max:
        issues.append("Notification threshold minimum must be positive and below maximum")
    for setting_name in (
        "GRADSYNC_NOTIFICATION_REMINDER_LEAD_MINUTES",
        "GRADSYNC_NOTIFICATION_ESCALATION_DELAY_MINUTES",
        "GRADSYNC_NOTIFICATION_REPEAT_INTERVAL_MINUTES",
    ):
        value = getattr(settings_obj, setting_name, 1440)
        if not threshold_min <= value <= threshold_max:
            issues.append(f"{setting_name} must be within notification threshold bounds")
    if not 0 <= getattr(settings_obj, "GRADSYNC_NOTIFICATION_MAX_REMINDERS", 3) <= 20:
        issues.append("GRADSYNC_NOTIFICATION_MAX_REMINDERS must be between 0 and 20")
    if not 1 <= getattr(settings_obj, "GRADSYNC_REPORT_ANALYTICS_MAX_PERIODS", 104) <= 104:
        issues.append("GRADSYNC_REPORT_ANALYTICS_MAX_PERIODS must be between 1 and 104")
    if not 0 <= getattr(settings_obj, "GRADSYNC_REPORT_ANALYTICS_CACHE_SECONDS", 60) <= 3600:
        issues.append("GRADSYNC_REPORT_ANALYTICS_CACHE_SECONDS must be between 0 and 3600")
    if not 1 <= getattr(settings_obj, "GRADSYNC_EXECUTION_JOB_BATCH_SIZE", 200) <= 1000:
        issues.append("GRADSYNC_EXECUTION_JOB_BATCH_SIZE must be between 1 and 1000")
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
        "PRODUCTION_SMTP_PROBE_TO",
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
            for volume_name in (
                "GRADSYNC_POSTGRES_VOLUME_NAME",
                "GRADSYNC_MEDIA_VOLUME_NAME",
            ):
                if volume_name not in compose_text:
                    issues.append(f"production compose must use a stable {volume_name} volume name")
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
                "DEPLOY_REVISION: ${{ github.sha }}",
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
                'REVISION="${GRADSYNC_DEPLOY_REVISION:-}"',
                'git checkout --detach "$REVISION"',
                'test "$(git rev-parse HEAD)" = "$REVISION"',
                "docker compose",
                "python manage.py check --deploy",
                "/healthz/",
                "/readyz/",
                "/api/schema/",
            ):
                if required not in deploy_text:
                    issues.append(f"deploy script is missing {required}")
        notification_tasks = repo_root / "backend/apps/notifications/tasks.py"
        task_text = notification_tasks.read_text() if notification_tasks.exists() else ""
        for required_task in (
            "maintain_reporting_periods_task",
            "create_risk_review_reminders_task",
            "process_actionable_notification_followups_task",
        ):
            if required_task not in task_text:
                issues.append(f"execution scheduler registration is missing {required_task}")
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
        "EMAIL_HOST": "smtp.gradsync.edu",
        "EMAIL_PORT": 587,
        "EMAIL_HOST_USER": "smtp-user",
        "EMAIL_HOST_PASSWORD": "smtp-password",
        "EMAIL_USE_TLS": True,
        "EMAIL_USE_SSL": False,
        "EMAIL_TIMEOUT": 10,
        "DEFAULT_FROM_EMAIL": "no-reply@gradsync.edu",
        "CELERY_BROKER_URL": "redis://redis:6379/0",
        "CELERY_NOTIFICATION_QUEUE": "notifications",
        "CELERY_TASK_ROUTES": {"apps.notifications.tasks.*": {"queue": "notifications"}},
        "GRADSYNC_NOTIFICATION_REMINDER_LEAD_MINUTES": 1440,
        "GRADSYNC_NOTIFICATION_ESCALATION_DELAY_MINUTES": 1440,
        "GRADSYNC_NOTIFICATION_REPEAT_INTERVAL_MINUTES": 1440,
        "GRADSYNC_NOTIFICATION_MAX_REMINDERS": 3,
        "GRADSYNC_NOTIFICATION_THRESHOLD_MIN_MINUTES": 60,
        "GRADSYNC_NOTIFICATION_THRESHOLD_MAX_MINUTES": 10080,
        "GRADSYNC_REPORT_ANALYTICS_MAX_PERIODS": 104,
        "GRADSYNC_REPORT_ANALYTICS_CACHE_SECONDS": 60,
        "GRADSYNC_EXECUTION_JOB_BATCH_SIZE": 200,
        "PUBLIC_BASE_URL": "https://gradsync.edu",
        "TLS_CERTIFICATE_PATH": "/etc/letsencrypt/live/gradsync.edu/fullchain.pem",
        "TLS_PRIVATE_KEY_PATH": "/etc/letsencrypt/live/gradsync.edu/privkey.pem",
        "EMAIL_PROVIDER": "smtp-provider",
        "EMAIL_PROVIDER_DOMAIN": "gradsync.edu",
        "EMAIL_DKIM_SELECTOR": "gradsync",
        "PRODUCTION_SMTP_PROBE_TO": "ops@gradsync.edu",
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
