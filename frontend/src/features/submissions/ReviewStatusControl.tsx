import { useMutation } from '@tanstack/react-query';

import { useAppFeedback } from '../../shared/ui/AppFeedback';
import type { DraftVersion, WeeklyReport } from './api';
import { reviewDraftVersion, reviewWeeklyReport } from './api';

type Props = {
  status: string;
  projectId?: number;
  draftId?: number;
  versionId?: number;
  reportId?: number;
  targetType?: 'draft' | 'report';
};

export function ReviewStatusControl({ status, projectId, draftId, versionId, reportId, targetType = 'report' }: Props) {
  const { notify } = useAppFeedback();
  const mutation = useMutation<DraftVersion | WeeklyReport | null, Error, string>({
    mutationFn: (reviewStatus: string) => {
      if (!projectId) return Promise.resolve(null);
      if (targetType === 'draft' && draftId && versionId) {
        return reviewDraftVersion(projectId, draftId, versionId, reviewStatus);
      }
      if (reportId) {
        return reviewWeeklyReport(projectId, reportId, reviewStatus);
      }
      return Promise.resolve(null);
    },
    onSuccess: () => notify('Review status updated', 'success'),
    onError: (error) => notify(error.message, 'error'),
  });

  return (
    <label>
      Review status
      <select defaultValue={status} onChange={(event) => mutation.mutate(event.target.value)}>
        <option value="pending_review">Pending review</option>
        <option value="reviewed">Reviewed</option>
        <option value="needs_revision">Needs revision</option>
        <option value="closed">Closed</option>
      </select>
      {mutation.isSuccess ? <span role="status">Review status updated</span> : null}
      {mutation.error ? <span role="alert">{mutation.error.message}</span> : null}
    </label>
  );
}
