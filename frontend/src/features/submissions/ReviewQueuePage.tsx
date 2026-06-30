import { useQuery } from '@tanstack/react-query';
import { useParams } from 'react-router-dom';

import { listDrafts, listReports } from './api';
import { InlineCommentPanel } from './InlineCommentPanel';
import { ReviewStatusControl } from './ReviewStatusControl';

export function ReviewQueuePage() {
  const projectId = Number(useParams().projectId ?? 0);
  const draftsQuery = useQuery({ queryKey: ['review-drafts', projectId], queryFn: () => listDrafts(projectId), enabled: Boolean(projectId) });
  const reportsQuery = useQuery({ queryKey: ['review-reports', projectId], queryFn: () => listReports(projectId), enabled: Boolean(projectId) });

  return (
    <section className="review-workspace">
      <div className="page-heading">
        <div>
          <h1>Review queue</h1>
          <p>Open pending student submissions, add anchored comments, and update review status.</p>
        </div>
      </div>
      <div className="two-column-workspace">
        <section className="panel" aria-label="Submission review">
          <h2>Submission preview</h2>
          <section aria-label="Draft reviews">
            <h3>Draft reviews</h3>
            <p>{draftsQuery.data?.results.length ?? 0} draft families loaded</p>
            <ul className="resource-list">
              {draftsQuery.data?.results.map((draft) => (
                <li key={draft.id}>
                  <strong>{draft.title}</strong>
                  <span>{draft.status}</span>
                </li>
              ))}
            </ul>
          </section>
          <section aria-label="Report reviews">
            <h3>Report reviews</h3>
            <ul className="resource-list">
              {reportsQuery.data?.results.map((report) => (
                <li key={report.id}>
                  <div>
                    <strong>Week {report.report_week_start}</strong>
                    <p>{report.completed_work}</p>
                  </div>
                  <ReviewStatusControl projectId={projectId} reportId={report.id} status={report.review_status} targetType="report" />
                </li>
              ))}
            </ul>
          </section>
        </section>
        <InlineCommentPanel projectId={projectId} targetType="progress_report" targetId={reportsQuery.data?.results[0]?.id} />
      </div>
    </section>
  );
}
