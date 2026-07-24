from django.core.exceptions import ValidationError as DjangoValidationError
from django.shortcuts import get_object_or_404
from django.utils import timezone
from drf_spectacular.utils import OpenApiParameter, OpenApiResponse, extend_schema
from rest_framework import status, views
from rest_framework.exceptions import ValidationError
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from apps.common.downloads import DownloadUnavailable, storage_file_download_response
from apps.common.pagination import parse_id_cursor
from apps.common.permissions import IsAdministrator

from .export_services import (
    audit_queryset,
    create_audit_export,
    normalize_audit_filters,
)
from .models import AuditEvent, AuditExport
from .serializers import AuditEventSerializer, AuditExportSerializer
from .services import record_event
from .tasks import generate_audit_export_task


class AdministratorAuditView(views.APIView):
    permission_classes = [IsAuthenticated, IsAdministrator]


class AuditEventListView(AdministratorAuditView):
    @extend_schema(
        parameters=[
            OpenApiParameter(name, value_type, OpenApiParameter.QUERY)
            for name, value_type in (
                ("startsAt", str),
                ("endsAt", str),
                ("actorId", int),
                ("projectId", int),
                ("category", str),
                ("outcome", str),
                ("targetType", str),
                ("targetId", str),
                ("q", str),
                ("cursor", str),
                ("limit", int),
            )
        ],
        responses={
            200: AuditEventSerializer(many=True),
            400: OpenApiResponse(description="Validation failed"),
            403: OpenApiResponse(description="Administrator access required"),
        },
    )
    def get(self, request):
        filters = normalize_audit_filters(request.query_params)
        cursor = parse_id_cursor(request.query_params.get("cursor"))
        try:
            limit = max(1, min(int(request.query_params.get("limit", 50)), 100))
        except ValueError as exc:
            raise ValidationError({"limit": "Enter a number from 1 to 100."}) from exc
        queryset = audit_queryset(filters)
        if cursor:
            queryset = queryset.filter(id__lt=cursor)
        rows = list(queryset[: limit + 1])
        has_more = len(rows) > limit
        rows = rows[:limit]
        next_cursor = str(rows[-1].id) if has_more and rows else None
        payload = AuditEventSerializer(rows, many=True).data
        record_event(
            None,
            request.user,
            "audit_access.search",
            "Audit events searched",
            category=AuditEvent.Category.AUDIT_ACCESS,
            target_snapshot={"resultCount": len(payload)},
            allowed_snapshot_keys={"resultCount"},
        )
        return Response(
            {
                "results": payload,
                "nextCursor": next_cursor,
                "capabilities": {"canExport": True},
            }
        )


class AuditEventDetailView(AdministratorAuditView):
    @extend_schema(
        responses={
            200: AuditEventSerializer,
            403: OpenApiResponse(description="Administrator access required"),
            404: OpenApiResponse(description="Audit event not found"),
        }
    )
    def get(self, request, event_id):
        event = get_object_or_404(AuditEvent, pk=event_id)
        payload = AuditEventSerializer(event).data
        payload["capabilities"] = {"canExport": True}
        record_event(
            None,
            request.user,
            "audit_access.detail_viewed",
            "Audit event detail viewed",
            event,
            category=AuditEvent.Category.AUDIT_ACCESS,
            target_snapshot={"eventId": event.id},
            allowed_snapshot_keys={"eventId"},
        )
        return Response(payload)


class AuditExportCreateView(AdministratorAuditView):
    @extend_schema(
        request={
            "application/json": {
                "type": "object",
                "properties": {"filters": {"type": "object"}},
                "required": ["filters"],
            }
        },
        responses={
            202: AuditExportSerializer,
            400: OpenApiResponse(description="Validation failed"),
            403: OpenApiResponse(description="Administrator access required"),
            409: OpenApiResponse(description="Export conflict"),
            429: OpenApiResponse(description="Rate limited"),
        },
    )
    def post(self, request):
        try:
            export = create_audit_export(
                requested_by=request.user,
                filters=request.data.get("filters", {}),
            )
        except DjangoValidationError as exc:
            raise ValidationError({"message": exc.messages[0]}) from exc
        generate_audit_export_task.delay(str(export.id))
        export.refresh_from_db()
        return Response(
            AuditExportSerializer(export, context={"request": request}).data,
            status=status.HTTP_202_ACCEPTED,
        )


class AuditExportDetailView(AdministratorAuditView):
    @extend_schema(
        responses={
            200: AuditExportSerializer,
            403: OpenApiResponse(description="Administrator access required"),
            404: OpenApiResponse(description="Audit export not found"),
        }
    )
    def get(self, request, export_id):
        export = get_object_or_404(
            AuditExport,
            pk=export_id,
            requested_by=request.user,
        )
        if export.status == AuditExport.Status.READY and export.expires_at <= timezone.now():
            export.status = AuditExport.Status.EXPIRED
            export.save(update_fields=["status"])
        return Response(AuditExportSerializer(export, context={"request": request}).data)


class AuditExportDownloadView(AdministratorAuditView):
    @extend_schema(
        responses={
            200: OpenApiResponse(description="Audit export CSV"),
            403: OpenApiResponse(description="Administrator access required"),
            404: OpenApiResponse(description="Audit export not found"),
            409: OpenApiResponse(description="Audit export unavailable"),
        }
    )
    def get(self, request, export_id):
        export = get_object_or_404(
            AuditExport.objects.select_related("file"),
            pk=export_id,
            requested_by=request.user,
        )
        if (
            export.status != AuditExport.Status.READY
            or export.expires_at <= timezone.now()
            or not export.file
        ):
            return Response(
                {"message": "Audit export is not available."},
                status=status.HTTP_409_CONFLICT,
            )
        record_event(
            None,
            request.user,
            "audit_access.export_downloaded",
            "Audit export downloaded",
            export,
            category=AuditEvent.Category.AUDIT_ACCESS,
            target_snapshot={"exportedCount": export.exported_count},
            allowed_snapshot_keys={"exportedCount"},
        )
        try:
            return storage_file_download_response(
                export.file.stored_name,
                filename=export.file.original_filename,
                content_type="text/csv",
            )
        except DownloadUnavailable as exc:
            return Response({"message": str(exc)}, status=status.HTTP_410_GONE)
