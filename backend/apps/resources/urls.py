from django.urls import include, path
from rest_framework.routers import DefaultRouter

from .views import (
    BookingViewSet,
    LaboratoryResourceViewSet,
    ResourceItemViewSet,
    ResourceTypeViewSet,
    ResourceUseSubmissionViewSet,
    StandaloneBookingViewSet,
)

resource_router = DefaultRouter()
resource_router.register("resource-types", ResourceTypeViewSet, basename="resource-types")
resource_router.register("resource-items", ResourceItemViewSet, basename="resource-items")
resource_router.register("resources", LaboratoryResourceViewSet, basename="resources")
resource_router.register("bookings", StandaloneBookingViewSet, basename="bookings")
resource_router.register(
    "resource-use-submissions",
    ResourceUseSubmissionViewSet,
    basename="resource-use-submissions",
)

booking_router = DefaultRouter()
booking_router.register("bookings", BookingViewSet, basename="project-bookings")

urlpatterns = [
    path("", include(resource_router.urls)),
    path("projects/<int:project_id>/", include(booking_router.urls)),
]
