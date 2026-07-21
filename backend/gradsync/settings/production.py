import os

from apps.common.error_reporting import configure_error_reporting

from .base import *  # noqa: F403,F405


def _required_env(name: str) -> str:
    value = os.getenv(name, "").strip()
    if not value:
        raise RuntimeError(f"{name} must be set for production")
    return value


def _csv_env(name: str, *, required: bool = False) -> list[str]:
    raw = os.getenv(name, "").strip()
    if required and not raw:
        raise RuntimeError(f"{name} must be set for production")
    return [item.strip() for item in raw.split(",") if item.strip()]


DEBUG = False

SECRET_KEY = _required_env("DJANGO_SECRET_KEY")
if (
    SECRET_KEY in {"dev-secret-key", "change-me", "replace-with-a-64-character-random-secret"}
    or len(SECRET_KEY) < 32
):
    raise RuntimeError("DJANGO_SECRET_KEY must be a non-default secret at least 32 characters long")

ALLOWED_HOSTS = _csv_env("DJANGO_ALLOWED_HOSTS", required=True)
if "*" in ALLOWED_HOSTS:
    raise RuntimeError("DJANGO_ALLOWED_HOSTS cannot contain '*' in production")

CSRF_TRUSTED_ORIGINS = _csv_env("DJANGO_CSRF_TRUSTED_ORIGINS", required=True)
FRONTEND_ORIGIN = _required_env("FRONTEND_ORIGIN")

SESSION_COOKIE_SECURE = True
CSRF_COOKIE_SECURE = True
SESSION_COOKIE_HTTPONLY = True
CSRF_COOKIE_HTTPONLY = False
SECURE_SSL_REDIRECT = os.getenv("DJANGO_SECURE_SSL_REDIRECT", "true").lower() == "true"
SECURE_PROXY_SSL_HEADER = ("HTTP_X_FORWARDED_PROTO", "https")
SECURE_HSTS_SECONDS = int(os.getenv("DJANGO_SECURE_HSTS_SECONDS", "31536000"))
SECURE_HSTS_INCLUDE_SUBDOMAINS = (
    os.getenv("DJANGO_SECURE_HSTS_INCLUDE_SUBDOMAINS", "true").lower() == "true"
)
SECURE_HSTS_PRELOAD = os.getenv("DJANGO_SECURE_HSTS_PRELOAD", "true").lower() == "true"
SECURE_CONTENT_TYPE_NOSNIFF = True
X_FRAME_OPTIONS = "DENY"

DATABASES["default"].update(  # noqa: F405
    {
        "CONN_MAX_AGE": int(os.getenv("POSTGRES_CONN_MAX_AGE", "60")),
        "OPTIONS": {"sslmode": os.getenv("POSTGRES_SSLMODE", "prefer")},
    }
)

if DATABASES["default"]["PASSWORD"] in {  # noqa: F405
    "",
    "gradsync",
    "password",
    "replace-with-a-strong-database-password",
}:
    raise RuntimeError("POSTGRES_PASSWORD must be set to a non-default value in production")

STORAGES = {
    "default": {
        "BACKEND": "django.core.files.storage.FileSystemStorage",
    },
    "staticfiles": {
        "BACKEND": "django.contrib.staticfiles.storage.ManifestStaticFilesStorage",
    },
}

EMAIL_HOST = _required_env("EMAIL_HOST")
DEFAULT_FROM_EMAIL = _required_env("DEFAULT_FROM_EMAIL")
EMAIL_SUBJECT_PREFIX = os.getenv("EMAIL_SUBJECT_PREFIX", "[GradSync] ")

PUBLIC_BASE_URL = os.getenv("PUBLIC_BASE_URL", "").strip()
TLS_CERTIFICATE_PATH = os.getenv("TLS_CERTIFICATE_PATH", "").strip()
TLS_PRIVATE_KEY_PATH = os.getenv("TLS_PRIVATE_KEY_PATH", "").strip()
EMAIL_PROVIDER = os.getenv("EMAIL_PROVIDER", "").strip()
EMAIL_PROVIDER_DOMAIN = os.getenv("EMAIL_PROVIDER_DOMAIN", "").strip()
EMAIL_DKIM_SELECTOR = os.getenv("EMAIL_DKIM_SELECTOR", "").strip()
PRODUCTION_SMTP_PROBE_TO = os.getenv("PRODUCTION_SMTP_PROBE_TO", "").strip()
ALERT_WEBHOOK_URL = os.getenv("ALERT_WEBHOOK_URL", "").strip()
ALERT_ONCALL_TARGET = os.getenv("ALERT_ONCALL_TARGET", "").strip()
REGISTRY_IMAGE_PREFIX = os.getenv("REGISTRY_IMAGE_PREFIX", "").strip()
BACKEND_IMAGE = os.getenv("BACKEND_IMAGE", "").strip()
FRONTEND_IMAGE = os.getenv("FRONTEND_IMAGE", "").strip()
POSTGRES_BACKUP_OFFSITE_URI = os.getenv("POSTGRES_BACKUP_OFFSITE_URI", "").strip()
BACKUP_RESTORE_DRILL_EVIDENCE = os.getenv("BACKUP_RESTORE_DRILL_EVIDENCE", "").strip()

SPECTACULAR_SETTINGS["SERVERS"] = [  # noqa: F405
    {"url": os.getenv("PUBLIC_API_BASE_URL", "/api")}
]

ERROR_REPORTING_ENABLED = configure_error_reporting()
