from django.db.models.signals import post_save
from django.dispatch import receiver

from apps.projects.models import ProjectMembership

from .audience_services import reresolve_audience
from .models import ScheduleItem


@receiver(post_save, sender=ProjectMembership)
def refresh_project_schedule_grants(sender, instance, **kwargs):
    items = ScheduleItem.objects.filter(
        scope=ScheduleItem.Scope.GROUP,
        audiences__project_id=instance.project_id,
    ).distinct()
    for item in items:
        reresolve_audience(item)
