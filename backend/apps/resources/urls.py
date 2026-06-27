from django.urls import include, path
from rest_framework.routers import DefaultRouter

from .views import BookingViewSet, LabResourceViewSet

resource_router = DefaultRouter()
resource_router.register("resources", LabResourceViewSet, basename="resources")

booking_router = DefaultRouter()
booking_router.register("bookings", BookingViewSet, basename="project-bookings")

urlpatterns = [
    path("", include(resource_router.urls)),
    path("projects/<int:project_id>/", include(booking_router.urls)),
]
