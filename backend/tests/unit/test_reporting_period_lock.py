from datetime import timedelta

import pytest
from django.utils import timezone

from apps.projects.models import ProjectMembership, ResearchProject
from apps.submissions.report_period_services import open_reporting_period
from apps.submissions.report_template_services import (
    create_template_draft,
    publish_template_version,
    replace_template_fields,
)
from tests.factories.accounts import VerifiedUserFactory
from tests.factories.collaboration import ProjectMembershipFactory, ResearchProjectFactory


@pytest.mark.django_db
def test_period_locks_one_published_version_and_is_idempotent():
    advisor = VerifiedUserFactory(global_role="advisor", active_role="teacher")
    project = ResearchProjectFactory(advisor=advisor)
    ProjectMembershipFactory(
        project=project, user=advisor, role=ProjectMembership.Role.ADVISOR
    )
    version = create_template_draft(actor=advisor, project=project, name="Weekly")
    replace_template_fields(
        actor=advisor,
        template_version=version,
        expected_version=1,
        fields=[
            {
                "key": "completed",
                "label_en": "Completed work",
                "label_zh": "已完成工作",
                "field_type": "long_text",
                "required": True,
                "order": 0,
            }
        ],
    )
    publish_template_version(
        actor=advisor, template_version=version, expected_version=2
    )
    starts_on = timezone.localdate()
    first = open_reporting_period(project=project, starts_on=starts_on)
    second = open_reporting_period(project=project, starts_on=starts_on)
    assert first.id == second.id
    assert first.template_version_id == version.id
    assert first.ends_on == starts_on + timedelta(days=7)

    project.status = ResearchProject.Status.ARCHIVED
    project.save(update_fields=["status"])
    with pytest.raises(ValueError, match="Archived"):
        open_reporting_period(project=project, starts_on=starts_on + timedelta(days=7))
