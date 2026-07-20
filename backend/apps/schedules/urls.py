from django.urls import path

from .views import (
    CalendarEventView,
    CalendarOccurrenceView,
    ScheduleAudienceOptionsView,
    ScheduleCancelView,
    ScheduleCollectionView,
    ScheduleCompleteView,
    ScheduleConflictView,
    ScheduleDeliveryStatusView,
    ScheduleDetailView,
    SchedulePublishView,
    ScheduleRevisionView,
)

app_name = "schedules"
urlpatterns = [
    path("calendar/occurrences/", CalendarOccurrenceView.as_view(), name="calendar-occurrences"),
    path("calendar/events/", CalendarEventView.as_view(), name="calendar-events"),
    path("schedules/", ScheduleCollectionView.as_view(), name="schedule-create"),
    path(
        "schedules/audience-options/",
        ScheduleAudienceOptionsView.as_view(),
        name="schedule-audience-options",
    ),
    path("schedules/conflicts/", ScheduleConflictView.as_view(), name="schedule-conflicts"),
    path("schedules/<int:schedule_id>/", ScheduleDetailView.as_view(), name="schedule-detail"),
    path(
        "schedules/<int:schedule_id>/publish/",
        SchedulePublishView.as_view(),
        name="schedule-publish",
    ),
    path(
        "schedules/<int:schedule_id>/complete/",
        ScheduleCompleteView.as_view(),
        name="schedule-complete",
    ),
    path(
        "schedules/<int:schedule_id>/cancel/",
        ScheduleCancelView.as_view(),
        name="schedule-cancel",
    ),
    path(
        "schedules/<int:schedule_id>/revisions/",
        ScheduleRevisionView.as_view(),
        name="schedule-revisions",
    ),
    path(
        "schedules/<int:schedule_id>/delivery-status/",
        ScheduleDeliveryStatusView.as_view(),
        name="schedule-delivery-status",
    ),
]
