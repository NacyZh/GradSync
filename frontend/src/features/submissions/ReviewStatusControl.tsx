import { useMutation } from '@tanstack/react-query';

import { Label } from '@/shared/ui/primitives/label';
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
  disabled?: boolean;
};

export function ReviewStatusControl({ status, projectId, draftId, versionId, reportId, targetType = 'report', disabled = false }: Props) {
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
    <div className="grid gap-2">
      <Label htmlFor={`review-status-${targetType}-${reportId ?? versionId ?? 'target'}`}>Review status</Label>
      <select
        id={`review-status-${targetType}-${reportId ?? versionId ?? 'target'}`}
        defaultValue={status}
        onChange={(event) => mutation.mutate(event.target.value)}
        aria-label="Review status"
        disabled={disabled || mutation.isPending}
      >
        <option value="pending_review">Pending review</option>
        <option value="reviewed">Reviewed</option>
        <option value="needs_revision">Needs revision</option>
        <option value="closed">Closed</option>
      </select>
      {disabled ? <span className="text-sm text-muted-foreground">Review controls are disabled for archived or unauthorized targets.</span> : null}
      {mutation.isSuccess ? <span role="status">Review status updated</span> : null}
      {mutation.error ? <span role="alert">{mutation.error.message}</span> : null}
    </div>
  );
}
