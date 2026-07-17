import { useMutation } from '@tanstack/react-query';

import { Label } from '@/shared/ui/primitives/label';
import { useAppFeedback } from '../../shared/ui/AppFeedback';
import type { WeeklyReport } from './api';
import { reviewWeeklyReport } from './api';

type Props = {
  status: string;
  projectId?: number;
  reportId?: number;
  disabled?: boolean;
};

export function ReviewStatusControl({ status, projectId, reportId, disabled = false }: Props) {
  const { notify } = useAppFeedback();
  const mutation = useMutation<WeeklyReport | null, Error, string>({
    mutationFn: (reviewStatus: string) => {
      if (!projectId) return Promise.resolve(null);
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
      <Label htmlFor={`review-status-report-${reportId ?? 'target'}`}>Review status</Label>
      <select
        id={`review-status-report-${reportId ?? 'target'}`}
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
