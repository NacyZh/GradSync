import factory
from django.utils import timezone

from apps.schedules.models import ScheduleItem
from apps.submissions.models import ProjectReportSchedule
from tests.factories.accounts import UserFactory
from tests.factories.collaboration import ResearchProjectFactory


class ScheduleItemFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = ScheduleItem

    owner = factory.SubFactory(UserFactory)
    organizer = factory.SelfAttribute("owner")
    title = factory.Sequence(lambda n: f"Schedule item {n}")
    starts_at = factory.LazyFunction(lambda: timezone.now() + timezone.timedelta(days=1))
    ends_at = factory.LazyAttribute(lambda obj: obj.starts_at + timezone.timedelta(hours=1))
    timezone = "UTC"


class ProjectReportScheduleFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = ProjectReportSchedule

    project = factory.SubFactory(ResearchProjectFactory)
    updated_by = factory.SelfAttribute("project.advisor")
    weekday = 4
    deadline_time = timezone.datetime.min.time().replace(hour=17)
    timezone = "UTC"
