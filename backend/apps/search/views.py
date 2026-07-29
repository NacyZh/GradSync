from drf_spectacular.utils import OpenApiParameter, OpenApiResponse, extend_schema
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.common.permissions import IsActiveAccount

from .serializers import GlobalSearchQuerySerializer, GlobalSearchResponseSerializer
from .services import global_search


class GlobalSearchView(APIView):
    permission_classes = [IsAuthenticated, IsActiveAccount]

    @extend_schema(
        parameters=[
            OpenApiParameter("q", str, OpenApiParameter.QUERY, required=True),
            OpenApiParameter("limit", int, OpenApiParameter.QUERY),
        ],
        responses={
            200: GlobalSearchResponseSerializer,
            400: OpenApiResponse(description="Invalid search query"),
            401: OpenApiResponse(description="Authentication required"),
            403: OpenApiResponse(description="Active account required"),
        },
    )
    def get(self, request):
        query_serializer = GlobalSearchQuerySerializer(data=request.query_params)
        query_serializer.is_valid(raise_exception=True)
        payload = global_search(
            user=request.user,
            query=query_serializer.validated_data["q"],
            per_type_limit=query_serializer.validated_data["limit"],
        )
        return Response(GlobalSearchResponseSerializer(payload).data)
