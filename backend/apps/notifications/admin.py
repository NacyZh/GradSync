from django.contrib import admin

from .models import Notification


@admin.register(Notification)
class NotificationAdmin(admin.ModelAdmin):
    list_display = ("project", "recipient", "event_type", "status", "eligible_at", "sent_at")
    list_filter = ("event_type", "status")
    search_fields = ("subject", "recipient__email", "project__title")
