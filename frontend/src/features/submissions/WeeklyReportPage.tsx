import { useMutation } from '@tanstack/react-query';
import { useParams } from 'react-router-dom';
import { useCallback, useRef } from 'react';
import { ClipboardCheck } from 'lucide-react';

import { Button } from '@/shared/ui/primitives/button';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/shared/ui/primitives/card';
import { KeyboardHint, useAppFeedback, useSubmitShortcut } from '../../shared/ui/AppFeedback';
import { FieldGroup, FormField, TextareaField } from '../../shared/ui/FormField';
import { FormStatus } from '../../shared/ui/FormStatus';
import { PageShell } from '../../shared/ui/PageShell';
import { WeeklyReportHistory } from './WeeklyReportHistory';
import { submitWeeklyReport } from './api';

export function WeeklyReportPage() {
  const projectId = Number(useParams().projectId ?? 0);
  const formRef = useRef<HTMLFormElement>(null);
  const { notify } = useAppFeedback();
  const mutation = useMutation({
    mutationFn: submitWeeklyReport.bind(null, projectId),
    onSuccess: () => notify('Weekly report submitted', 'success'),
    onError: (error) => notify(error.message, 'error'),
  });

  function onSubmit(event: React.FormEvent<HTMLFormElement>) {
    event.preventDefault();
    const form = new FormData(event.currentTarget);
    mutation.mutate({
      report_week_start: String(form.get('reportWeekStart')),
      completed_work: String(form.get('completedWork')),
      blockers: String(form.get('blockers') ?? ''),
      next_steps: String(form.get('nextSteps')),
    });
  }

  const submitShortcut = useCallback(() => {
    formRef.current?.requestSubmit();
  }, []);
  useSubmitShortcut(submitShortcut);

  return (
    <PageShell
      title="Weekly progress report"
      description="Summarize completed work, blockers, and next steps for advisor review."
      className="submission-workspace"
    >
      <div className="grid gap-4 xl:grid-cols-[minmax(24rem,1.2fr)_minmax(18rem,0.8fr)]">
        <Card>
          <CardHeader>
            <CardTitle className="flex items-center gap-2">
              <ClipboardCheck className="h-4 w-4" aria-hidden="true" />
              Report editor
            </CardTitle>
            <CardDescription>Submit one project-scoped weekly update for review.</CardDescription>
          </CardHeader>
          <CardContent>
            <form ref={formRef} className="rich-report-form" aria-label="Weekly progress report" onSubmit={onSubmit}>
              <FieldGroup>
                <FormField id="report-week-start" name="reportWeekStart" label="Week start" type="date" required disabled={mutation.isPending} />
                <TextareaField id="report-completed-work" name="completedWork" label="Completed work" required placeholder="Paste images as links or describe attached evidence." disabled={mutation.isPending} className="editor-field" />
                <TextareaField id="report-blockers" name="blockers" label="Blockers" placeholder="Risks, dependencies, or advisor decisions needed." disabled={mutation.isPending} className="editor-field" />
                <TextareaField id="report-next-steps" name="nextSteps" label="Next steps" required disabled={mutation.isPending} className="editor-field" />
              </FieldGroup>
              <div className="action-row">
                <Button type="submit" disabled={mutation.isPending}>Submit report</Button>
                <KeyboardHint>Ctrl+Enter submits</KeyboardHint>
              </div>
              <FormStatus error={mutation.error?.message} success={mutation.isSuccess ? 'Weekly report submitted' : undefined} />
            </form>
          </CardContent>
        </Card>
        <WeeklyReportHistory reports={mutation.data ? [mutation.data] : []} />
      </div>
    </PageShell>
  );
}
