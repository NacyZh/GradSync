import pytest

from apps.projects.models import ProjectMembership
from apps.submissions.report_template_services import (
    create_template_draft,
    publish_template_version,
    replace_template_fields,
)
from tests.factories.accounts import VerifiedUserFactory
from tests.factories.collaboration import ProjectMembershipFactory, ResearchProjectFactory


@pytest.mark.django_db
def test_template_supports_only_controlled_bilingual_field_types():
    advisor = VerifiedUserFactory(global_role="advisor", active_role="teacher")
    project = ResearchProjectFactory(advisor=advisor)
    ProjectMembershipFactory(
        project=project, user=advisor, role=ProjectMembership.Role.ADVISOR
    )
    version = create_template_draft(actor=advisor, project=project, name="Weekly")
    fields = [
        {
            "key": field_type,
            "label_en": field_type,
            "label_zh": f"zh-{field_type}",
            "field_type": field_type,
            "required": True,
            "order": index,
            **(
                {
                    "options": [
                        {"value": "one", "labelEn": "One", "labelZh": "一"}
                    ]
                }
                if field_type in {"single_choice", "multiple_choice"}
                else {}
            ),
        }
        for index, field_type in enumerate(
            [
                "long_text",
                "number",
                "percentage",
                "single_choice",
                "multiple_choice",
                "execution_progress",
                "risk_blocker",
            ]
        )
    ]
    replace_template_fields(
        actor=advisor,
        template_version=version,
        expected_version=1,
        fields=fields,
    )
    published = publish_template_version(
        actor=advisor, template_version=version, expected_version=2
    )
    assert published.fields.count() == 7
    with pytest.raises(ValueError, match="published"):
        replace_template_fields(
            actor=advisor,
            template_version=published,
            expected_version=2,
            fields=fields,
        )


@pytest.mark.django_db
def test_template_rejects_missing_bilingual_label_and_arbitrary_formula():
    advisor = VerifiedUserFactory(global_role="advisor", active_role="teacher")
    project = ResearchProjectFactory(advisor=advisor)
    ProjectMembershipFactory(
        project=project, user=advisor, role=ProjectMembership.Role.ADVISOR
    )
    version = create_template_draft(actor=advisor, project=project, name="Weekly")
    with pytest.raises(ValueError):
        replace_template_fields(
            actor=advisor,
            template_version=version,
            expected_version=1,
            fields=[
                {
                    "key": "score",
                    "label_en": "Score",
                    "label_zh": "",
                    "field_type": "formula",
                    "required": True,
                    "order": 0,
                }
            ],
        )
