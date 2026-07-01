import { useQuery } from '@tanstack/react-query';
import { useParams } from 'react-router-dom';
import { BookOpenCheck, FileSearch, NotebookPen } from 'lucide-react';

import { Badge } from '@/components/ui/badge';
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs';
import { DataState } from '../../shared/ui/DataState';
import { PageShell } from '../../shared/ui/PageShell';
import { StatusBadge } from '../../shared/ui/StatusBadge';
import { listDrafts, listReports } from './api';
import { InlineCommentPanel } from './InlineCommentPanel';
import { ReviewStatusControl } from './ReviewStatusControl';

export function ReviewQueuePage() {
  const projectId = Number(useParams().projectId ?? 0);
  const draftsQuery = useQuery({ queryKey: ['review-drafts', projectId], queryFn: () => listDrafts(projectId), enabled: Boolean(projectId) });
  const reportsQuery = useQuery({ queryKey: ['review-reports', projectId], queryFn: () => listReports(projectId), enabled: Boolean(projectId) });
  const firstReport = reportsQuery.data?.results[0];
  const drafts = draftsQuery.data?.results ?? [];
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
              <p className="text-sm text-muted-foreground">Draft families and weekly reports stay project-scoped.</p>
            </div>
            <Badge variant="secondary">{drafts.length + reports.length} loaded</Badge>
          </div>
          <Tabs defaultValue="reports">
            <TabsList aria-label="Review target type">
              <TabsTrigger value="reports">Reports</TabsTrigger>
              <TabsTrigger value="drafts">Drafts</TabsTrigger>
            </TabsList>
            <TabsContent value="reports">
              <section aria-label="Report reviews" className="grid gap-3">
                <h3 className="sr-only">Report reviews</h3>
                {reportsQuery.isLoading ? <DataState state="loading" message="Loading reports" /> : null}
                {!reportsQuery.isLoading && reports.length === 0 ? <DataState state="empty" title="No reports" message="No weekly reports are waiting for review." /> : null}
                <ul className="resource-list">
                  {reports.map((report) => (
                    <li key={report.id}>
                      <div className="min-w-0">
                        <strong className="flex items-center gap-2">
                          <NotebookPen className="h-4 w-4 text-primary" aria-hidden="true" />
                          Week {report.report_week_start}
                        </strong>
                        <p>{report.completed_work}</p>
                        <small className="text-muted-foreground">Target progress_report #{report.id}</small>
                      </div>
                      <ReviewStatusControl projectId={projectId} reportId={report.id} status={report.review_status} targetType="report" />
                    </li>
                  ))}
                </ul>
              </section>
            </TabsContent>
            <TabsContent value="drafts">
              <section aria-label="Draft reviews" className="grid gap-3">
                <h3 className="sr-only">Draft reviews</h3>
                {draftsQuery.isLoading ? <DataState state="loading" message="Loading drafts" /> : null}
                {!draftsQuery.isLoading && drafts.length === 0 ? <DataState state="empty" title="No drafts" message="No draft families are loaded for review." /> : null}
                <ul className="resource-list">
                  {drafts.map((draft) => (
                    <li key={draft.id}>
                      <strong className="flex items-center gap-2">
                        <BookOpenCheck className="h-4 w-4 text-primary" aria-hidden="true" />
                        {draft.title}
                      </strong>
                      <StatusBadge status={draft.status} />
                    </li>
                  ))}
                </ul>
              </section>
            </TabsContent>
          </Tabs>
        </section>
        <InlineCommentPanel projectId={projectId} targetType="progress_report" targetId={firstReport?.id} />
      </div>
    </PageShell>
  );
}
