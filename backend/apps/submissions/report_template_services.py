from __future__ import annotations

from decimal import Decimal, InvalidOperation

from django.core.exceptions import PermissionDenied
from django.db import transaction
from django.db.models import Max
from django.utils import timezone

from apps.audit.services import record_execution_event
from apps.projects.access_services import project_capabilities

from .models import ReportTemplate, ReportTemplateField, ReportTemplateVersion

CHOICE_TYPES = {
    ReportTemplateField.FieldType.SINGLE_CHOICE,
    ReportTemplateField.FieldType.MULTIPLE_CHOICE,
}
NUMERIC_TYPES = {
    ReportTemplateField.FieldType.NUMBER,
    ReportTemplateField.FieldType.PERCENTAGE,
}
ANALYTICS_TYPES = NUMERIC_TYPES | {
    ReportTemplateField.FieldType.EXECUTION_PROGRESS,
    ReportTemplateField.FieldType.RISK_BLOCKER,
}


def _require_template_manager(actor, project):
    if not project_capabilities(actor, project)["canManageReportTemplates"]:
        raise PermissionDenied("Only the primary advisor can manage report templates.")


def _decimal(value):
    if value in {None, ""}:
        return None
    try:
        return Decimal(str(value))
    except InvalidOperation as exc:
        raise ValueError("Enter a valid numeric bound.") from exc


def validate_field_definition(data):
    field_type = data.get("field_type")
    if field_type not in ReportTemplateField.FieldType.values:
        raise ValueError("Select a supported report field type.")
    if not str(data.get("key", "")).strip():
        raise ValueError("A stable field key is required.")
    if not str(data.get("label_en", "")).strip() or not str(data.get("label_zh", "")).strip():
        raise ValueError("English and Chinese field labels are required.")
    options = data.get("options") or []
    if field_type in CHOICE_TYPES:
        if not 1 <= len(options) <= 50:
            raise ValueError("Choice fields require between 1 and 50 options.")
        values = [str(item.get("value", "")).strip() for item in options]
        if any(
            not value
            or not str(item.get("labelEn", "")).strip()
            or not str(item.get("labelZh", "")).strip()
            for value, item in zip(values, options, strict=True)
        ) or len(values) != len(set(values)):
            raise ValueError("Choice values and bilingual labels must be unique.")
    elif options:
        raise ValueError("Options apply only to choice fields.")
    minimum = _decimal(data.get("min_value"))
    maximum = _decimal(data.get("max_value"))
    if field_type == ReportTemplateField.FieldType.PERCENTAGE:
        minimum, maximum = Decimal("0"), Decimal("100")
    elif field_type not in NUMERIC_TYPES and (minimum is not None or maximum is not None):
        raise ValueError("Numeric bounds apply only to numeric fields.")
    if minimum is not None and maximum is not None and minimum > maximum:
        raise ValueError("Minimum value cannot exceed maximum value.")
    unit = str(data.get("unit", "")).strip()
    if unit and field_type != ReportTemplateField.FieldType.NUMBER:
        raise ValueError("Units apply only to number fields.")
    analytics_enabled = bool(data.get("analytics_enabled", False))
    if analytics_enabled and field_type not in ANALYTICS_TYPES:
        raise ValueError("Analytics are not supported for this field type.")
    return {
        "key": str(data["key"]).strip(),
        "label_en": str(data["label_en"]).strip(),
        "label_zh": str(data["label_zh"]).strip(),
        "help_text_en": str(data.get("help_text_en", "")).strip(),
        "help_text_zh": str(data.get("help_text_zh", "")).strip(),
        "field_type": field_type,
        "required": bool(data.get("required", False)),
        "order": int(data["order"]),
        "unit": unit,
        "options": options,
        "min_value": minimum,
        "max_value": maximum,
        "analytics_enabled": analytics_enabled,
    }


@transaction.atomic
def create_template_draft(*, actor, project, name):
    _require_template_manager(actor, project)
    template, _ = ReportTemplate.objects.get_or_create(
        project=project,
        defaults={"name": name.strip(), "created_by": actor},
    )
    existing = template.versions.filter(status=ReportTemplateVersion.Status.DRAFT).first()
    if existing:
        return existing
    next_number = (template.versions.aggregate(value=Max("version_number"))["value"] or 0) + 1
    version = ReportTemplateVersion.objects.create(
        project=project,
        template=template,
        version_number=next_number,
        created_by=actor,
    )
    if template.active_version_id:
        ReportTemplateField.objects.bulk_create(
            [
                ReportTemplateField(
                    template_version=version,
                    key=field.key,
                    label_en=field.label_en,
                    label_zh=field.label_zh,
                    help_text_en=field.help_text_en,
                    help_text_zh=field.help_text_zh,
                    field_type=field.field_type,
                    required=field.required,
                    order=field.order,
                    unit=field.unit,
                    options=field.options,
                    min_value=field.min_value,
                    max_value=field.max_value,
                    analytics_enabled=field.analytics_enabled,
                )
                for field in template.active_version.fields.all()
            ]
        )
    record_execution_event(
        project=project,
        actor=actor,
        action="report_template.draft_created",
        target=version,
        state={"status": version.status, "version": version.version},
    )
    return version


@transaction.atomic
def replace_template_fields(*, actor, template_version, expected_version: int, fields: list[dict]):
    version = (
        ReportTemplateVersion.objects.select_for_update()
        .select_related("project")
        .get(pk=template_version.pk)
    )
    _require_template_manager(actor, version.project)
    if version.status != ReportTemplateVersion.Status.DRAFT:
        raise ValueError("Only a draft can be edited; this version is published.")
    if version.version != expected_version:
        raise ValueError("The report template changed; refresh and try again.")
    if not 1 <= len(fields) <= 50:
        raise ValueError("A template requires between 1 and 50 fields.")
    normalized = [validate_field_definition(item) for item in fields]
    keys = [item["key"] for item in normalized]
    orders = [item["order"] for item in normalized]
    if len(keys) != len(set(keys)) or len(orders) != len(set(orders)):
        raise ValueError("Field keys and order values must be unique.")
    version.fields.all().delete()
    ReportTemplateField.objects.bulk_create(
        [ReportTemplateField(template_version=version, **item) for item in normalized]
    )
    version.version += 1
    version.save(update_fields=["version"])
    return version


@transaction.atomic
def publish_template_version(*, actor, template_version, expected_version: int):
    version = (
        ReportTemplateVersion.objects.select_for_update()
        .select_related("project", "template")
        .get(pk=template_version.pk)
    )
    _require_template_manager(actor, version.project)
    if version.status == ReportTemplateVersion.Status.PUBLISHED:
        return version
    if version.status != ReportTemplateVersion.Status.DRAFT:
        raise ValueError("Only a draft template can be published.")
    if version.version != expected_version:
        raise ValueError("The report template changed; refresh and try again.")
    fields = list(version.fields.all())
    if not fields:
        raise ValueError("Publish at least one valid template field.")
    for field in fields:
        validate_field_definition(
            {
                "key": field.key,
                "label_en": field.label_en,
                "label_zh": field.label_zh,
                "help_text_en": field.help_text_en,
                "help_text_zh": field.help_text_zh,
                "field_type": field.field_type,
                "required": field.required,
                "order": field.order,
                "unit": field.unit,
                "options": field.options,
                "min_value": field.min_value,
                "max_value": field.max_value,
                "analytics_enabled": field.analytics_enabled,
            }
        )
    version.template.versions.filter(status=ReportTemplateVersion.Status.PUBLISHED).update(
        status=ReportTemplateVersion.Status.SUPERSEDED
    )
    version.status = ReportTemplateVersion.Status.PUBLISHED
    version.published_by = actor
    version.published_at = timezone.now()
    version.save(update_fields=["status", "published_by", "published_at"])
    version.template.active_version = version
    version.template.save(update_fields=["active_version", "updated_at"])
    record_execution_event(
        project=version.project,
        actor=actor,
        action="report_template.published",
        target=version,
        state={"status": version.status, "version": version.version},
        privileged=True,
    )
    return version


@transaction.atomic
def ensure_default_report_template(*, actor, project):
    template = (
        ReportTemplate.objects.select_related("active_version").filter(project=project).first()
    )
    if template and template.active_version_id:
        return template.active_version
    draft = create_template_draft(actor=actor, project=project, name="Weekly progress")
    if not draft.fields.exists():
        replace_template_fields(
            actor=actor,
            template_version=draft,
            expected_version=draft.version,
            fields=[
                {
                    "key": "completed_work",
                    "label_en": "Completed work",
                    "label_zh": "已完成工作",
                    "field_type": "long_text",
                    "required": True,
                    "order": 0,
                },
                {
                    "key": "blockers",
                    "label_en": "Blockers",
                    "label_zh": "阻碍事项",
                    "field_type": "risk_blocker",
                    "required": False,
                    "order": 1,
                    "analytics_enabled": True,
                },
                {
                    "key": "next_steps",
                    "label_en": "Next steps",
                    "label_zh": "下一步计划",
                    "field_type": "long_text",
                    "required": True,
                    "order": 2,
                },
                {
                    "key": "progress_percent",
                    "label_en": "Progress",
                    "label_zh": "进度",
                    "field_type": "percentage",
                    "required": False,
                    "order": 3,
                    "analytics_enabled": True,
                },
            ],
        )
        draft.refresh_from_db()
    return publish_template_version(
        actor=actor, template_version=draft, expected_version=draft.version
    )
