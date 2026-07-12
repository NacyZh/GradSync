import pytest
from django.utils import timezone

from apps.projects.models import ProjectMembership, ResearchProject
from apps.resources.models import ResourceItem, ResourceType
from tests.factories.accounts import UserFactory
from tests.helpers import authenticate


@pytest.mark.django_db
def test_resource_list_and_booking_create(api_client):
    student = UserFactory(global_role="student")
    advisor = UserFactory(global_role="advisor")
    project = ResearchProject.objects.create(title="Project", advisor=advisor)
    ProjectMembership.objects.create(project=project, user=student, role="student")
    resource_type = ResourceType.objects.create(
        name="Lab seat",
        field_schema=[
            {
                "key": "capacity",
                "label": "Capacity",
                "fieldType": "number",
                "required": False,
            }
        ],
    )
    resource = ResourceItem.objects.create(
        resource_type=resource_type,
        name="Seat 1",
        location="Lab",
        field_values={"capacity": 1},
    )

    resources_response = authenticate(api_client, student).get("/api/resource-items/")
    assert resources_response.status_code == 200

    starts_at = timezone.now() + timezone.timedelta(days=2)
    ends_at = starts_at + timezone.timedelta(hours=1)

    booking_response = api_client.post(
        f"/api/projects/{project.id}/bookings/",
        {
            "resourceItemId": resource.id,
            "starts_at": starts_at.isoformat(),
            "ends_at": ends_at.isoformat(),
        },
        format="json",
    )
    assert booking_response.status_code == 201
