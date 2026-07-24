import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import { UserCheck } from 'lucide-react';
import { useState } from 'react';

import { getProject } from '@/features/projects';
import { useAppFeedback } from '@/shared/ui/AppFeedback';
import { Button } from '@/shared/ui/primitives/button';
import { Label } from '@/shared/ui/primitives/label';
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/shared/ui/primitives/select';

import { assignReportReviewer, listReviewAssignments } from './api';
import { useI18n } from '@/shared/i18n/I18nProvider';

export function ReviewerAssignmentControl({
  projectId,
  reportId,
}: {
  projectId: number;
  reportId: number;
}) {
  const { t } = useI18n();
  const { notify } = useAppFeedback();
  const queryClient = useQueryClient();
  const [membershipId, setMembershipId] = useState('');
  const projectQuery = useQuery({
    queryKey: ['project', projectId],
    queryFn: () => getProject(projectId),
  });
  const assignmentsQuery = useQuery({
    queryKey: ['review-assignments', projectId, reportId],
    queryFn: () => listReviewAssignments(projectId),
  });
  const reviewers = (projectQuery.data?.memberships ?? []).filter(
    (member) => member.role === 'reviewer' && member.status === 'active',
  );
  const current = (assignmentsQuery.data?.results ?? []).filter(
    (assignment) => assignment.weeklyReportId === reportId && assignment.status === 'active',
  );
  const mutation = useMutation({
    mutationFn: () =>
      assignReportReviewer(projectId, {
        reviewerMembershipId: Number(membershipId),
        weeklyReportId: reportId,
      }),
    onSuccess: async () => {
      setMembershipId('');
      notify('Reviewer assigned', 'success');
      await queryClient.invalidateQueries({ queryKey: ['review-assignments', projectId] });
    },
    onError: (error) => notify(error.message, 'error'),
  });

  if (!projectQuery.data?.capabilities?.canAssignReviews) return null;

  return (
    <section className="grid gap-3 rounded-md border p-4" aria-label={t('reviewerAssignment')}>
      <h3 className="mb-0 flex items-center gap-2">
        <UserCheck className="h-4 w-4" aria-hidden="true" />
        {t('assignedReviewers')}
      </h3>
      {current.length ? (
        <ul className="text-sm text-muted-foreground">
          {current.map((assignment) => (
            <li key={assignment.id}>{assignment.reviewerName || `Reviewer ${assignment.reviewerMembershipId}`}</li>
          ))}
        </ul>
      ) : (
        <p className="text-sm text-muted-foreground">{t('noReviewerAssigned')}</p>
      )}
      <div className="grid gap-2 sm:grid-cols-[minmax(0,1fr)_auto]">
        <div className="grid gap-1.5">
          <Label>{t('reviewer')}</Label>
          <Select value={membershipId} onValueChange={setMembershipId}>
            <SelectTrigger><SelectValue placeholder={t('selectProjectReviewer')} /></SelectTrigger>
            <SelectContent>
              {reviewers.map((reviewer) => (
                <SelectItem key={reviewer.id} value={String(reviewer.id)}>
                  {reviewer.nickname || reviewer.name || reviewer.email}
                </SelectItem>
              ))}
            </SelectContent>
          </Select>
        </div>
        <Button className="self-end" type="button" onClick={() => mutation.mutate()} disabled={!membershipId || mutation.isPending}>
          {t('assign')}
        </Button>
      </div>
    </section>
  );
}
