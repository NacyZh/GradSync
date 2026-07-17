from django.core.exceptions import PermissionDenied, ValidationError
from django.utils import timezone

from apps.audit.services import record_event
from apps.common.project_scope import ProjectScopedService
from apps.notifications.models import Notification
from apps.projects.archive_services import ensure_project_writable

from .models import WeeklyProgressReport


class WeeklyReportService(ProjectScopedService):
    def __init__(self, user, project):
        super().__init__(user)
        self.project = project

    def submit_report(self, **data) -> WeeklyProgressReport:
        self.require_project_member(self.project)
        ensure_project_writable(self.project)
        if not self.project.memberships.filter(
            user=self.user, status="active", role="student"
        ).exists():
            raise PermissionDenied("Only project students can submit weekly reports")
        existing_reports = WeeklyProgressReport.objects.filter(
            project=self.project,
            student=self.user,
            report_week_start=data["report_week_start"],
        ).order_by("-revision_number", "-submitted_at")
        latest = existing_reports.first()
        if latest and latest.review_status != WeeklyProgressReport.ReviewStatus.NEEDS_REVISION:
            raise ValidationError(
                "A weekly report already exists for this project week. Wait for review or choose a different week."
            )
        report = WeeklyProgressReport.objects.create(
            project=self.project,
            student=self.user,
            revision_number=(latest.revision_number + 1 if latest else 1),
            **data,
        )
        for membership in self.project.memberships.filter(
            role__in=["advisor", "reviewer"], status="active"
        ):
            Notification.objects.create(
                project=self.project,
                recipient=membership.user,
                event_type=Notification.EventType.NEW_SUBMISSION,
                target_type="WeeklyProgressReport",
                target_id=str(report.id),
                subject="New weekly progress report submitted",
                action_path=f"/projects/{self.project.id}/reports/{report.id}",
                sender=self.user,
                eligible_at=timezone.now(),
            )
        record_event(
            self.project,
            self.user,
            "weekly_report.submitted",
            f"Submitted weekly progress report revision {report.revision_number}",
            report,
        )
        return report

    def update_review_status(
        self, report: WeeklyProgressReport, review_status: str
    ) -> WeeklyProgressReport:
        self.require_project_reviewer(self.project)
        ensure_project_writable(self.project)
        report.review_status = review_status
        report.reviewed_at = timezone.now()
        report.save(update_fields=["review_status", "reviewed_at"])
        record_event(
            self.project,
            self.user,
            "weekly_report.reviewed",
            f"Set weekly report {report.id} to {review_status}",
            report,
        )
        return report
