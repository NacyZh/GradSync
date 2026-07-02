from django.core.exceptions import ValidationError

SUPPORTED_LOCALES = {"en", "zh"}


def get_locale(user) -> str:
    return user.locale if getattr(user, "locale", "") in SUPPORTED_LOCALES else "en"


def set_locale(user, locale: str) -> str:
    if locale not in SUPPORTED_LOCALES:
        raise ValidationError("Unsupported locale")
    user.locale = locale
    user.save(update_fields=["locale"])
    return user.locale
