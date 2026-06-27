import { useQuery } from '@tanstack/react-query';
import { useParams } from 'react-router-dom';

import { listDrafts, listReports } from './api';
import { ReviewStatusControl } from './ReviewStatusControl';

export function ReviewQueuePage() {
  const projectId = Number(useParams().projectId ?? 0);
  const draftsQuery = useQuery({ queryKey: ['review-drafts', projectId], queryFn: () => listDrafts(projectId), enabled: Boolean(projectId) });
  const reportsQuery = useQuery({ queryKey: ['review-reports', projectId], queryFn: () => listReports(projectId), enabled: Boolean(projectId) });

  return (
    <section>
      <h1>Review queue</h1>
      <section aria-label="Draft reviews">
        <h2>Draft reviews</h2>
        <p>{draftsQuery.data?.results.length ?? 0} draft families loaded</p>
      </section>
      <section aria-label="Report reviews">
        <h2>Report reviews</h2>
        <ul>
          {reportsQuery.data?.results.map((report) => (
            <li key={report.id}>
              Week {report.report_week_start}
              <ReviewStatusControl projectId={projectId} reportId={report.id} status={report.review_status} targetType="report" />
            </li>
          ))}
        </ul>
      </section>
    </section>
  );
}
