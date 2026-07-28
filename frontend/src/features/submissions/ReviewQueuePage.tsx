import { useEffect, useMemo, useState } from 'react';
import { useQuery } from '@tanstack/react-query';
import { useParams } from 'react-router-dom';
import { FileSearch, MessageSquareText, NotebookPen, PackageCheck } from 'lucide-react';

import { Badge } from '@/shared/ui/primitives/badge';
import { Button } from '@/shared/ui/primitives/button';
import { Tabs, TabsList, TabsTrigger } from '@/shared/ui/primitives/tabs';
import { formatUiDate } from '@/shared/i18n/translate';
import { useI18n } from '@/shared/i18n/I18nProvider';
import { DataState } from '../../shared/ui/DataState';
import { PageShell } from '../../shared/ui/PageShell';
import { StatusBadge } from '../../shared/ui/StatusBadge';
import { listReports, type WeeklyReport } from './api';
import { InlineCommentPanel } from './InlineCommentPanel';
import { ReviewStatusControl } from './ReviewStatusControl';
import { ReviewerAssignmentControl } from './ReviewerAssignmentControl';
import {
  DeliverableDetail,
  listDeliverables,
  type Deliverable,
} from '../projects';

export function ReviewQueuePage() {
  const { t } = useI18n();
  const projectId = Number(useParams().projectId ?? 0);
  const reportsQuery = useQuery({ queryKey: ['review-reports', projectId], queryFn: () => listReports(projectId), enabled: Boolean(projectId) });
  const deliverablesQuery = useQuery({
    queryKey: ['project-deliverables', projectId, 'review-queue'],
    queryFn: () =>
      listDeliverables(projectId, {
        status: 'under_review',
        pageSize: 100,
      }),
    enabled: Boolean(projectId),
  });
  const reports = useMemo(() => reportsQuery.data?.results ?? [], [reportsQuery.data?.results]);
  const deliverables = useMemo(
    () => deliverablesQuery.data?.results ?? [],
    [deliverablesQuery.data?.results],
  );
  const [queueType, setQueueType] = useState<'reports' | 'deliverables'>('reports');
  const [selectedReportId, setSelectedReportId] = useState<number | null>(null);
  const [selectedDeliverableId, setSelectedDeliverableId] = useState<number | null>(null);
  const selectedReport = useMemo(
    () => reports.find((report) => report.id === selectedReportId) ?? reports[0],
    [reports, selectedReportId],
  );
  const selectedDeliverable = useMemo(
    () =>
      deliverables.find((item) => item.id === selectedDeliverableId) ??
      deliverables[0],
    [deliverables, selectedDeliverableId],
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
  useEffect(() => {
    if (!deliverables.length) {
      setSelectedDeliverableId(null);
      return;
    }
    if (
      !selectedDeliverableId ||
      !deliverables.some((item) => item.id === selectedDeliverableId)
    ) {
      setSelectedDeliverableId(deliverables[0].id);
    }
  }, [deliverables, selectedDeliverableId]);

  return (
    <PageShell
      title="Review queue"
      description="Open pending student submissions, add anchored comments, and update review status."
      className="review-workspace"
    >
      <Tabs
        value={queueType}
        onValueChange={(value) => setQueueType(value as 'reports' | 'deliverables')}
      >
        <TabsList aria-label={t('reviewTargetType')}>
          <TabsTrigger value="reports">
            <NotebookPen className="mr-2 h-4 w-4" />
            Reports
          </TabsTrigger>
          <TabsTrigger value="deliverables">
            <PackageCheck className="mr-2 h-4 w-4" />
            Deliverables
          </TabsTrigger>
        </TabsList>
      </Tabs>
      <div className="grid min-w-0 gap-4 xl:grid-cols-[minmax(18rem,0.42fr)_minmax(0,1fr)]">
        <section className="panel grid max-h-[min(42rem,calc(100vh-11rem))] min-h-[28rem] min-w-0 grid-rows-[auto_auto_1fr] overflow-hidden" aria-label="Review queue list">
          <div className="mb-4 flex flex-wrap items-start justify-between gap-3">
            <div>
              <h2 className="flex items-center gap-2">
                <FileSearch className="h-4 w-4" aria-hidden="true" />
                {queueType === 'reports' ? 'Reports' : 'Deliverables'}
              </h2>
              <p className="text-sm text-muted-foreground">
                {queueType === 'reports'
                  ? 'Select one report to review details and comments.'
                  : 'Select one deliverable revision to record a recommendation or final decision.'}
              </p>
            </div>
            <Badge variant="secondary">
              {queueType === 'reports' ? reports.length : deliverables.length} loaded
            </Badge>
          </div>
          {queueType === 'reports' && reportsQuery.isLoading ? <DataState state="loading" message="Loading reports" /> : null}
          {queueType === 'deliverables' && deliverablesQuery.isLoading ? <DataState state="loading" message={t('loadingDeliverables')} /> : null}
          {queueType === 'reports' && !reportsQuery.isLoading && reports.length === 0 ? <DataState state="empty" title="No reports" message="No weekly reports are waiting for review." /> : null}
          {queueType === 'deliverables' && !deliverablesQuery.isLoading && deliverables.length === 0 ? <DataState state="empty" title={t('noDeliverables')} message={t('noDeliverableReviews')} /> : null}
          {queueType === 'reports' ? (
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
          ) : (
            <DeliverableReviewList
              deliverables={deliverables}
              selectedId={selectedDeliverable?.id}
              onSelect={setSelectedDeliverableId}
              revisionLabel={t('revisionLowercase')}
              listLabel={t('deliverableReviews')}
            />
          )}
        </section>
        {queueType === 'reports' ? (
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
        ) : (
          <section
            className="panel h-[min(42rem,calc(100vh-11rem))] min-h-[28rem] min-w-0 overflow-hidden"
            aria-label="Deliverable review"
          >
            <DeliverableDetail
              projectId={projectId}
              deliverable={selectedDeliverable}
              materials={[]}
              onChanged={() => deliverablesQuery.refetch()}
            />
          </section>
        )}
      </div>
    </PageShell>
  );
}

function DeliverableReviewList({
  deliverables,
  selectedId,
  onSelect,
  revisionLabel,
  listLabel,
}: {
  deliverables: Deliverable[];
  selectedId?: number;
  onSelect: (id: number) => void;
  revisionLabel: string;
  listLabel: string;
}) {
  return (
    <ul
      className="resource-list min-h-0 overflow-y-auto pr-1"
      aria-label={listLabel}
    >
      {deliverables.map((deliverable) => (
        <li
          key={deliverable.id}
          className={
            deliverable.id === selectedId ? 'border-primary bg-primary/5' : undefined
          }
        >
          <Button
            type="button"
            variant="ghost"
            className="h-auto min-h-0 w-full justify-start p-0 text-left hover:bg-transparent"
            aria-pressed={deliverable.id === selectedId}
            onClick={() => onSelect(deliverable.id)}
          >
            <span className="grid min-w-0 gap-2">
              <strong className="truncate">{deliverable.title}</strong>
              <span className="flex flex-wrap items-center gap-2">
                <StatusBadge status={deliverable.status} />
                <span className="text-xs font-normal text-muted-foreground">
                  {revisionLabel} {deliverable.revisions[0]?.revisionNumber ?? 0}
                </span>
              </span>
              <span className="line-clamp-2 text-sm font-normal text-muted-foreground">
                {deliverable.acceptanceCriteria}
              </span>
            </span>
          </Button>
        </li>
      ))}
    </ul>
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
            {report.submitted_at ? ` · Submitted ${formatUiDate(report.submitted_at)}` : ''}
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
      <ReviewerAssignmentControl projectId={projectId} reportId={report.id} />
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
