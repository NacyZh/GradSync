import factory
from django.apps import apps
from django.utils import timezone

from apps.notifications.models import Notification
from apps.projects.models import ProjectMembership
from tests.factories.accounts import VerifiedUserFactory
from tests.factories.collaboration import ProjectMembershipFactory, ResearchProjectFactory


def execution_project(*, role=ProjectMembership.Role.ADVISOR, user=None, **overrides):
    user = user or VerifiedUserFactory(
        global_role="student" if role == ProjectMembership.Role.STUDENT else "advisor",
        active_role="student" if role == ProjectMembership.Role.STUDENT else "teacher",
    )
    project = ResearchProjectFactory(advisor=user, **overrides)
    ProjectMembershipFactory(project=project, user=user, role=role)
    return project, user


class ActionableNotificationFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = Notification

    recipient = factory.SubFactory(VerifiedUserFactory)
    event_type = Notification.EventType.APPROACHING_DEADLINE
    target_type = "Task"
    target_id = factory.Sequence(str)
    subject = factory.Sequence(lambda n: f"Action required {n}")
    eligible_at = factory.LazyFunction(timezone.now)
    category = Notification.Category.PROJECT
    requirement_type = Notification.RequirementType.ACTION
    outcome_state = Notification.OutcomeState.PENDING


def _execution_record(model_name: str, **overrides):
    model = apps.get_model("projects", model_name)
    return model.objects.create(**overrides)


def milestone(**overrides):
    return _execution_record("Milestone", **overrides)


def deliverable(**overrides):
    return _execution_record("Deliverable", **overrides)


def report_template(**overrides):
    return _execution_record("ReportTemplate", **overrides)


def reporting_period(**overrides):
    return _execution_record("ReportingPeriod", **overrides)


def decision(**overrides):
    return _execution_record("ProjectDecision", **overrides)


def risk(**overrides):
    return _execution_record("ProjectRisk", **overrides)
