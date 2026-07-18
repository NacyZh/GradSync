import { useQuery } from '@tanstack/react-query';
import { useParams } from 'react-router-dom';
import { FileSearch, NotebookPen } from 'lucide-react';

import { Badge } from '@/shared/ui/primitives/badge';
import { DataState } from '../../shared/ui/DataState';
import { PageShell } from '../../shared/ui/PageShell';
import { listReports } from './api';
import { InlineCommentPanel } from './InlineCommentPanel';
import { ReviewStatusControl } from './ReviewStatusControl';

export function ReviewQueuePage() {
  const projectId = Number(useParams().projectId ?? 0);
  const reportsQuery = useQuery({ queryKey: ['review-reports', projectId], queryFn: () => listReports(projectId), enabled: Boolean(projectId) });
  const firstReport = reportsQuery.data?.results[0];
  const reports = reportsQuery.data?.results ?? [];

  return (
    <PageShell
      title="Review queue"
      description="Open pending student submissions, add anchored comments, and update review status."
      className="review-workspace"
    >
      <div className="grid gap-4 xl:grid-cols-[minmax(24rem,1.15fr)_minmax(20rem,0.85fr)]">
        <section className="panel" aria-label="Submission review">
          <div className="mb-4 flex flex-wrap items-start justify-between gap-3">
            <div>
              <h2 className="flex items-center gap-2">
                <FileSearch className="h-4 w-4" aria-hidden="true" />
                Submission preview
              </h2>
              <p className="text-sm text-muted-foreground">Weekly reports stay project-scoped and keep returned revision history.</p>
            </div>
            <Badge variant="secondary">{reports.length} loaded</Badge>
          </div>
          <section aria-label="Report reviews" className="grid gap-3">
            <h3 className="sr-only">Report reviews</h3>
            {reportsQuery.isLoading ? <DataState state="loading" message="Loading reports" /> : null}
            {!reportsQuery.isLoading && reports.length === 0 ? <DataState state="empty" title="No reports" message="No weekly reports are waiting for review." /> : null}
            <ul className="resource-list">
              {reports.map((report) => (
                <li key={report.id}>
                  <div className="grid min-w-0 gap-3">
                    <strong className="flex items-center gap-2">
                      <NotebookPen className="h-4 w-4 text-primary" aria-hidden="true" />
                      Week {report.report_week_start}
                      {report.revision_number && report.revision_number > 1 ? ` · Revision ${report.revision_number}` : ''}
                    </strong>
                    <div className="grid gap-2 text-sm">
                      <section className="grid gap-1" aria-label={`Completed work for report ${report.id}`}>
                        <span className="font-semibold">Completed work</span>
                        <p className="whitespace-pre-wrap text-muted-foreground">{report.completed_work}</p>
                      </section>
                      {report.blockers ? (
                        <section className="grid gap-1" aria-label={`Blockers for report ${report.id}`}>
                          <span className="font-semibold">Blockers</span>
                          <p className="whitespace-pre-wrap text-muted-foreground">{report.blockers}</p>
                        </section>
                      ) : null}
                      <section className="grid gap-1" aria-label={`Next steps for report ${report.id}`}>
                        <span className="font-semibold">Next steps</span>
                        <p className="whitespace-pre-wrap text-muted-foreground">{report.next_steps}</p>
                      </section>
                    </div>
                    <small className="text-muted-foreground">
                      Target progress_report #{report.id} · Status {report.review_status.replaceAll('_', ' ')}
                      {report.submitted_at ? ` · Submitted ${new Date(report.submitted_at).toLocaleString()}` : ''}
                    </small>
                  </div>
                  <ReviewStatusControl projectId={projectId} reportId={report.id} status={report.review_status} />
                </li>
              ))}
            </ul>
          </section>
        </section>
        <InlineCommentPanel projectId={projectId} targetType="progress_report" targetId={firstReport?.id} />
      </div>
    </PageShell>
  );
}
