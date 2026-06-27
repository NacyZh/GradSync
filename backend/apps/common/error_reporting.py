import logging
import os

logger = logging.getLogger(__name__)
_configured = False


def configure_error_reporting() -> bool:
    global _configured
    dsn = os.getenv("SENTRY_DSN", "").strip()
    if not dsn:
        return False
    if _configured:
        return True
    try:
        import sentry_sdk
    except ImportError:
        logger.warning("SENTRY_DSN is set but sentry-sdk is not installed")
        return False
    sentry_sdk.init(
        dsn=dsn, traces_sample_rate=float(os.getenv("SENTRY_TRACES_SAMPLE_RATE", "0.0"))
    )
    _configured = True
    return True


def capture_exception(exc: BaseException) -> None:
    if not configure_error_reporting():
        logger.exception("Unhandled exception", exc_info=exc)
        return
    import sentry_sdk

    sentry_sdk.capture_exception(exc)
