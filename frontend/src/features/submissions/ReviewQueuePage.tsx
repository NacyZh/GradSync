import { useEffect, useMemo, useState } from 'react';
import { useQuery } from '@tanstack/react-query';
import { useParams } from 'react-router-dom';
import { FileSearch, MessageSquareText, NotebookPen } from 'lucide-react';

import { Badge } from '@/shared/ui/primitives/badge';
import { Button } from '@/shared/ui/primitives/button';
import { DataState } from '../../shared/ui/DataState';
import { PageShell } from '../../shared/ui/PageShell';
import { StatusBadge } from '../../shared/ui/StatusBadge';
import { listReports, type WeeklyReport } from './api';
import { InlineCommentPanel } from './InlineCommentPanel';
import { ReviewStatusControl } from './ReviewStatusControl';

export function ReviewQueuePage() {
  const projectId = Number(useParams().projectId ?? 0);
  const reportsQuery = useQuery({ queryKey: ['review-reports', projectId], queryFn: () => listReports(projectId), enabled: Boolean(projectId) });
  const reports = useMemo(() => reportsQuery.data?.results ?? [], [reportsQuery.data?.results]);
  const [selectedReportId, setSelectedReportId] = useState<number | null>(null);
  const selectedReport = useMemo(
    () => reports.find((report) => report.id === selectedReportId) ?? reports[0],
    [reports, selectedReportId],
  );

  useEffect(() => {
    if (reports.length === 0) {
      setSelectedReportId(null);
      return;
    }
    if (!selectedReportId || !reports.some((report) => report.id === selectedReportId)) {
      setSelectedReportId(reports[0].id);
    }
  }, [reports, selectedReportId]);

  return (
    <PageShell
      title="Review queue"
      description="Open pending student submissions, add anchored comments, and update review status."
      className="review-workspace"
    >
      <div className="grid min-w-0 gap-4 xl:grid-cols-[minmax(18rem,0.42fr)_minmax(0,1fr)]">
        <section className="panel grid max-h-[min(42rem,calc(100vh-11rem))] min-h-[28rem] min-w-0 grid-rows-[auto_auto_1fr] overflow-hidden" aria-label="Review queue list">
          <div className="mb-4 flex flex-wrap items-start justify-between gap-3">
            <div>
              <h2 className="flex items-center gap-2">
                <FileSearch className="h-4 w-4" aria-hidden="true" />
                Submissions
              </h2>
              <p className="text-sm text-muted-foreground">Select one report to review details and comments.</p>
            </div>
            <Badge variant="secondary">{reports.length} loaded</Badge>
          </div>
          {reportsQuery.isLoading ? <DataState state="loading" message="Loading reports" /> : null}
          {!reportsQuery.isLoading && reports.length === 0 ? <DataState state="empty" title="No reports" message="No weekly reports are waiting for review." /> : null}
          <ul className="resource-list min-h-0 overflow-y-auto pr-1" aria-label="Report reviews">
            {reports.map((report) => (
              <li key={report.id} className={report.id === selectedReport?.id ? 'border-primary bg-primary/5' : undefined}>
                <Button
                  type="button"
                  variant="ghost"
                  className="h-auto min-h-0 w-full justify-start p-0 text-left hover:bg-transparent"
                  aria-pressed={report.id === selectedReport?.id}
                  onClick={() => setSelectedReportId(report.id)}
                >
                  <span className="grid min-w-0 gap-2">
                    <strong className="flex min-w-0 items-center gap-2">
                      <NotebookPen className="h-4 w-4 flex-none text-primary" aria-hidden="true" />
                      <span className="truncate">{reportTitle(report)}</span>
                    </strong>
                    <span className="flex flex-wrap items-center gap-2">
                      <StatusBadge status={report.review_status} />
                      <span className="text-xs font-normal text-muted-foreground">progress_report #{report.id}</span>
                    </span>
                    <span className="line-clamp-2 text-sm font-normal text-muted-foreground">{report.completed_work}</span>
                  </span>
                </Button>
              </li>
            ))}
          </ul>
        </section>
        <section className="grid min-w-0 gap-4 xl:grid-cols-[minmax(0,1fr)_minmax(19rem,0.45fr)]">
          <section className="panel min-w-0" aria-label="Submission review">
            <ReviewDetail projectId={projectId} report={selectedReport} />
          </section>
          <InlineCommentPanel
            projectId={projectId}
            targetType="progress_report"
            targetId={selectedReport?.id}
            targetLabel={selectedReport ? reportTitle(selectedReport) : undefined}
          />
        </section>
      </div>
    </PageShell>
  );
}

function ReviewDetail({ projectId, report }: { projectId: number; report?: WeeklyReport }) {
  if (!report) {
    return <DataState state="empty" title="No report selected" message="Select a weekly report from the queue to review its details." />;
  }

  return (
    <div className="grid min-w-0 gap-5">
      <div className="flex flex-wrap items-start justify-between gap-3">
        <div className="min-w-0">
          <h2 className="flex min-w-0 items-center gap-2">
            <NotebookPen className="h-4 w-4 flex-none text-primary" aria-hidden="true" />
            <span className="truncate">{reportTitle(report)}</span>
          </h2>
          <p className="text-sm text-muted-foreground">
            Target progress_report #{report.id}
            {report.submitted_at ? ` · Submitted ${new Date(report.submitted_at).toLocaleString()}` : ''}
          </p>
        </div>
        <StatusBadge status={report.review_status} />
      </div>

      <div className="grid gap-3 rounded-md border bg-muted/20 p-4">
        <ReviewTextSection title="Completed work" label={`Completed work for report ${report.id}`} body={report.completed_work} />
        {report.blockers ? <ReviewTextSection title="Blockers" label={`Blockers for report ${report.id}`} body={report.blockers} /> : null}
        <ReviewTextSection title="Next steps" label={`Next steps for report ${report.id}`} body={report.next_steps} />
      </div>

      <div className="grid gap-3 rounded-md border p-4">
        <h3 className="mb-0 flex items-center gap-2">
          <MessageSquareText className="h-4 w-4 text-primary" aria-hidden="true" />
          Review decision
        </h3>
        <ReviewStatusControl projectId={projectId} reportId={report.id} status={report.review_status} />
      </div>
    </div>
  );
}

function ReviewTextSection({ title, label, body }: { title: string; label: string; body: string }) {
  return (
    <section className="grid gap-1" aria-label={label}>
      <h3 className="mb-0 text-sm font-bold">{title}</h3>
      <p className="whitespace-pre-wrap break-words text-sm text-muted-foreground">{body}</p>
    </section>
  );
}

function reportTitle(report: WeeklyReport) {
  return `Week ${report.report_week_start}${report.revision_number && report.revision_number > 1 ? ` · Revision ${report.revision_number}` : ''}`;
}
