from django.urls import include, path
from rest_framework.routers import DefaultRouter

from .views import BookingViewSet, ResourceItemViewSet, ResourceTypeViewSet

resource_router = DefaultRouter()
resource_router.register("resource-types", ResourceTypeViewSet, basename="resource-types")
resource_router.register("resource-items", ResourceItemViewSet, basename="resource-items")

booking_router = DefaultRouter()
booking_router.register("bookings", BookingViewSet, basename="project-bookings")

urlpatterns = [
    path("", include(resource_router.urls)),
    path("projects/<int:project_id>/", include(booking_router.urls)),
]
