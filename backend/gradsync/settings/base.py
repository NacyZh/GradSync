import os
from datetime import timedelta
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parents[2]


def _positive_int_env(name: str, default: int, *, minimum: int = 1) -> int:
    raw_value = os.getenv(name, str(default))
    try:
        value = int(raw_value)
    except ValueError as exc:
        raise RuntimeError(f"{name} must be an integer") from exc
    if value < minimum:
        raise RuntimeError(f"{name} must be at least {minimum}")
    return value


SECRET_KEY = os.getenv("DJANGO_SECRET_KEY", "dev-secret-key")
DEBUG = os.getenv("DJANGO_DEBUG", "false").lower() == "true"
ALLOWED_HOSTS = [host.strip() for host in os.getenv("DJANGO_ALLOWED_HOSTS", "localhost").split(",")]

INSTALLED_APPS = [
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",
    "rest_framework",
    "rest_framework_simplejwt.token_blacklist",
    "drf_spectacular",
    "django_celery_beat",
    "django_celery_results",
    "apps.common",
    "apps.accounts",
    "apps.projects",
    "apps.tasks",
    "apps.submissions",
    "apps.resources",
    "apps.library",
    "apps.repositories",
    "apps.operations",
    "apps.search",
    "apps.notifications",
    "apps.audit",
    "apps.schedules",
]

MIDDLEWARE = [
    "django.middleware.security.SecurityMiddleware",
    "apps.common.middleware.RequestIDMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
]

ROOT_URLCONF = "gradsync.urls"

TEMPLATES = [
    {
        "BACKEND": "django.template.backends.django.DjangoTemplates",
        "DIRS": [],
        "APP_DIRS": True,
        "OPTIONS": {
            "context_processors": [
                "django.template.context_processors.debug",
                "django.template.context_processors.request",
                "django.contrib.auth.context_processors.auth",
                "django.contrib.messages.context_processors.messages",
            ],
        },
    }
]

WSGI_APPLICATION = "gradsync.wsgi.application"
ASGI_APPLICATION = "gradsync.asgi.application"

DATABASES = {
    "default": {
        "ENGINE": "django.db.backends.postgresql",
        "NAME": os.getenv("POSTGRES_DB", "gradsync"),
        "USER": os.getenv("POSTGRES_USER", "gradsync"),
        "PASSWORD": os.getenv("POSTGRES_PASSWORD", "gradsync"),
        "HOST": os.getenv("POSTGRES_HOST", "localhost"),
        "PORT": os.getenv("POSTGRES_PORT", "5432"),
    }
}

AUTH_USER_MODEL = "accounts.User"

LANGUAGE_CODE = "en-us"
TIME_ZONE = "UTC"
USE_I18N = True
USE_TZ = True

STATIC_URL = "static/"
STATIC_ROOT = BASE_DIR / "staticfiles"
MEDIA_URL = "media/"
MEDIA_ROOT = BASE_DIR / "media"
DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"

# ── Session & CSRF ──
SESSION_COOKIE_AGE = int(os.getenv("SESSION_COOKIE_AGE", "1800"))  # 30 min default
SESSION_SAVE_EVERY_REQUEST = True  # Refresh session on each request
SESSION_EXPIRE_AT_BROWSER_CLOSE = (
    os.getenv("SESSION_EXPIRE_AT_BROWSER_CLOSE", "false").lower() == "true"
)
CSRF_COOKIE_SAMESITE = os.getenv("CSRF_COOKIE_SAMESITE", "Lax")
SESSION_COOKIE_SAMESITE = os.getenv("SESSION_COOKIE_SAMESITE", "Lax")
CSRF_TRUSTED_ORIGINS = [
    origin.strip()
    for origin in os.getenv(
        "DJANGO_CSRF_TRUSTED_ORIGINS", "http://localhost:5173,http://127.0.0.1:8080"
    ).split(",")
    if origin.strip()
]

REST_FRAMEWORK = {
    "DEFAULT_SCHEMA_CLASS": "drf_spectacular.openapi.AutoSchema",
    "DEFAULT_PAGINATION_CLASS": "apps.common.pagination.DefaultPagination",
    "EXCEPTION_HANDLER": "apps.common.exceptions.api_exception_handler",
    "DEFAULT_AUTHENTICATION_CLASSES": [
        "apps.accounts.authentication.ActiveAccountJWTAuthentication",
        "apps.accounts.authentication.ActiveAccountSessionAuthentication",
    ],
    "DEFAULT_PERMISSION_CLASSES": [
        "rest_framework.permissions.IsAuthenticated",
    ],
    "DEFAULT_THROTTLE_CLASSES": [
        "rest_framework.throttling.ScopedRateThrottle",
    ],
    "DEFAULT_THROTTLE_RATES": {
        "login": os.getenv("THROTTLE_LOGIN_RATE", "10/min"),
        "invite": os.getenv("THROTTLE_INVITE_RATE", "10/min"),
        "registration": os.getenv("THROTTLE_REGISTRATION_RATE", "5/min"),
        "password_recovery": os.getenv("GRADSYNC_RECOVERY_THROTTLE_RATE", "5/hour"),
        "email_security": os.getenv("GRADSYNC_EMAIL_SECURITY_THROTTLE_RATE", "10/hour"),
        "session_revocation": os.getenv("GRADSYNC_SESSION_REVOCATION_THROTTLE_RATE", "30/hour"),
        "paper_library": os.getenv("THROTTLE_PAPER_LIBRARY_RATE", "120/min"),
        "paper_import": os.getenv("THROTTLE_PAPER_IMPORT_RATE", "30/hour"),
        "calendar": os.getenv("THROTTLE_CALENDAR_RATE", "120/min"),
    },
}

SIMPLE_JWT = {
    "ACCESS_TOKEN_LIFETIME": timedelta(seconds=int(os.getenv("JWT_ACCESS_TOKEN_SECONDS", "300"))),
    "REFRESH_TOKEN_LIFETIME": timedelta(
        seconds=int(os.getenv("JWT_REFRESH_TOKEN_SECONDS", "604800"))
    ),
    "ROTATE_REFRESH_TOKENS": True,
    "BLACKLIST_AFTER_ROTATION": True,
    "UPDATE_LAST_LOGIN": False,
    "CHECK_REVOKE_TOKEN": True,
}

JWT_REFRESH_COOKIE_NAME = os.getenv("JWT_REFRESH_COOKIE_NAME", "gradsync_refresh")
JWT_REFRESH_COOKIE_PATH = "/api/accounts/"
JWT_REFRESH_COOKIE_SAMESITE = os.getenv("JWT_REFRESH_COOKIE_SAMESITE", "Strict")
JWT_REFRESH_COOKIE_SECURE = os.getenv("JWT_REFRESH_COOKIE_SECURE", "false").lower() == "true"

AUTH_PASSWORD_VALIDATORS = [
    {
        "NAME": "django.contrib.auth.password_validation.UserAttributeSimilarityValidator",
    },
    {
        "NAME": "django.contrib.auth.password_validation.MinimumLengthValidator",
        "OPTIONS": {"min_length": int(os.getenv("PASSWORD_MIN_LENGTH", "10"))},
    },
    {
        "NAME": "django.contrib.auth.password_validation.CommonPasswordValidator",
    },
    {
        "NAME": "django.contrib.auth.password_validation.NumericPasswordValidator",
    },
]

SPECTACULAR_SETTINGS = {
    "TITLE": "GradSync Research Group Operations API",
    "VERSION": "0.1.0",
    "POSTPROCESSING_HOOKS": [
        "apps.common.openapi.include_delete_request_bodies",
        "drf_spectacular.hooks.postprocess_schema_enums",
    ],
}

CELERY_BROKER_URL = os.getenv("REDIS_URL", "redis://localhost:6379/0")
CELERY_RESULT_BACKEND = "django-db"
CELERY_TIMEZONE = TIME_ZONE
CELERY_TASK_DEFAULT_QUEUE = os.getenv("CELERY_TASK_DEFAULT_QUEUE", "default")
CELERY_NOTIFICATION_QUEUE = os.getenv("CELERY_NOTIFICATION_QUEUE", "notifications")
CELERY_TASK_ROUTES = {
    "apps.notifications.tasks.*": {"queue": CELERY_NOTIFICATION_QUEUE},
}
CELERY_WORKER_PREFETCH_MULTIPLIER = int(os.getenv("CELERY_WORKER_PREFETCH_MULTIPLIER", "1"))
CELERY_TASK_TIME_LIMIT = int(os.getenv("CELERY_TASK_TIME_LIMIT", "300"))
CELERY_TASK_SOFT_TIME_LIMIT = int(os.getenv("CELERY_TASK_SOFT_TIME_LIMIT", "240"))

GRADSYNC_NOTIFICATION_REMINDER_LEAD_MINUTES = int(
    os.getenv("GRADSYNC_NOTIFICATION_REMINDER_LEAD_MINUTES", "1440")
)
GRADSYNC_NOTIFICATION_ESCALATION_DELAY_MINUTES = int(
    os.getenv("GRADSYNC_NOTIFICATION_ESCALATION_DELAY_MINUTES", "1440")
)
GRADSYNC_NOTIFICATION_REPEAT_INTERVAL_MINUTES = int(
    os.getenv("GRADSYNC_NOTIFICATION_REPEAT_INTERVAL_MINUTES", "1440")
)
GRADSYNC_NOTIFICATION_MAX_REMINDERS = int(
    os.getenv("GRADSYNC_NOTIFICATION_MAX_REMINDERS", "3")
)
GRADSYNC_NOTIFICATION_THRESHOLD_MIN_MINUTES = int(
    os.getenv("GRADSYNC_NOTIFICATION_THRESHOLD_MIN_MINUTES", "60")
)
GRADSYNC_NOTIFICATION_THRESHOLD_MAX_MINUTES = int(
    os.getenv("GRADSYNC_NOTIFICATION_THRESHOLD_MAX_MINUTES", "10080")
)
GRADSYNC_REPORT_ANALYTICS_MAX_PERIODS = int(
    os.getenv("GRADSYNC_REPORT_ANALYTICS_MAX_PERIODS", "104")
)
GRADSYNC_REPORT_ANALYTICS_CACHE_SECONDS = int(
    os.getenv("GRADSYNC_REPORT_ANALYTICS_CACHE_SECONDS", "60")
)
GRADSYNC_EXECUTION_JOB_BATCH_SIZE = int(os.getenv("GRADSYNC_EXECUTION_JOB_BATCH_SIZE", "200"))

EMAIL_HOST = os.getenv("EMAIL_HOST", "localhost")
EMAIL_PORT = int(os.getenv("EMAIL_PORT", "1025"))
EMAIL_HOST_USER = os.getenv("EMAIL_HOST_USER", "")
EMAIL_HOST_PASSWORD = os.getenv("EMAIL_HOST_PASSWORD", "")
EMAIL_USE_TLS = os.getenv("EMAIL_USE_TLS", "false").lower() == "true"
EMAIL_USE_SSL = os.getenv("EMAIL_USE_SSL", "false").lower() == "true"
EMAIL_TIMEOUT = int(os.getenv("EMAIL_TIMEOUT", "10"))
DEFAULT_FROM_EMAIL = os.getenv("DEFAULT_FROM_EMAIL", "no-reply@gradsync.local")
EMAIL_SUBJECT_PREFIX = os.getenv("EMAIL_SUBJECT_PREFIX", "[GradSync] ")

GRADSYNC_UPLOAD_MAX_BYTES = int(os.getenv("GRADSYNC_UPLOAD_MAX_BYTES", str(100 * 1024 * 1024)))
COLLABORATION_UPLOAD_LIMITS = {
    category: GRADSYNC_UPLOAD_MAX_BYTES
    for category in ("paper", "code", "document", "writing", "feedback")
}
PAPER_LIBRARY_UPLOAD_LIMIT_BYTES = GRADSYNC_UPLOAD_MAX_BYTES
DATA_UPLOAD_MAX_MEMORY_SIZE = int(
    os.getenv("DATA_UPLOAD_MAX_MEMORY_SIZE", str(GRADSYNC_UPLOAD_MAX_BYTES + 1024 * 1024))
)
FILE_UPLOAD_MAX_MEMORY_SIZE = int(os.getenv("FILE_UPLOAD_MAX_MEMORY_SIZE", str(2_621_440)))
PAPER_LIBRARY_EXTRACTION_TIMEOUT_SECONDS = int(
    os.getenv("PAPER_LIBRARY_EXTRACTION_TIMEOUT_SECONDS", "30")
)
PAPER_LIBRARY_DUPLICATE_STRONG_MATCH_THRESHOLD = float(
    os.getenv("PAPER_LIBRARY_DUPLICATE_STRONG_MATCH_THRESHOLD", "0.95")
)
PAPER_LIBRARY_DUPLICATE_FUZZY_MATCH_THRESHOLD = float(
    os.getenv("PAPER_LIBRARY_DUPLICATE_FUZZY_MATCH_THRESHOLD", "0.82")
)
PAPER_LIBRARY_MAINTAINER_REVIEW_VISIBLE = (
    os.getenv("PAPER_LIBRARY_MAINTAINER_REVIEW_VISIBLE", "true").lower() == "true"
)
EMAIL_VERIFICATION_CODE_TTL_MINUTES = int(os.getenv("EMAIL_VERIFICATION_CODE_TTL_MINUTES", "30"))
ROLE_ACTIVATION_TTL_DAYS = int(os.getenv("ROLE_ACTIVATION_TTL_DAYS", "14"))
ACCOUNT_RECOVERY_TOKEN_TTL_SECONDS = _positive_int_env("GRADSYNC_RECOVERY_TOKEN_TTL_SECONDS", 1800)
EMAIL_CHANGE_TOKEN_TTL_SECONDS = _positive_int_env("GRADSYNC_EMAIL_CHANGE_TOKEN_TTL_SECONDS", 1800)
APPROVED_FRONTEND_ORIGIN = (
    os.getenv(
        "GRADSYNC_APPROVED_FRONTEND_ORIGIN",
        os.getenv("FRONTEND_ORIGIN", "http://localhost:5173"),
    )
    .strip()
    .rstrip("/")
)
ACCOUNT_SESSION_ACTIVITY_UPDATE_SECONDS = _positive_int_env(
    "GRADSYNC_SESSION_ACTIVITY_UPDATE_SECONDS", 300
)
AUDIT_RETENTION_DAYS = _positive_int_env("GRADSYNC_AUDIT_RETENTION_DAYS", 365, minimum=365)
AUDIT_EXPORT_MAX_ROWS = _positive_int_env("GRADSYNC_AUDIT_EXPORT_MAX_ROWS", 10000)
AUDIT_EXPORT_TTL_SECONDS = _positive_int_env("GRADSYNC_AUDIT_EXPORT_TTL_SECONDS", 86400)

LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO")
LOGGING = {
    "version": 1,
    "disable_existing_loggers": False,
    "formatters": {
        "structured": {
            "format": (
                '{"time":"%(asctime)s","level":"%(levelname)s","logger":"%(name)s",'
                '"request_id":"%(request_id)s","message":"%(message)s"}'
            )
        },
    },
    "filters": {
        "request_id": {
            "()": "apps.common.middleware.RequestIDLogFilter",
        },
    },
    "handlers": {
        "console": {
            "class": "logging.StreamHandler",
            "formatter": "structured",
            "filters": ["request_id"],
        },
    },
    "root": {
        "handlers": ["console"],
        "level": LOG_LEVEL,
    },
}
