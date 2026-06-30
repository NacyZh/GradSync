import { useMutation } from '@tanstack/react-query';
import { useParams } from 'react-router-dom';
import { useCallback, useRef } from 'react';

import { KeyboardHint, useAppFeedback, useSubmitShortcut } from '../../shared/ui/AppFeedback';
import { FormStatus } from '../../shared/ui/FormStatus';
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
    <section className="submission-workspace">
      <div className="page-heading">
        <div>
          <h1>Weekly progress report</h1>
          <p>Summarize completed work, blockers, and next steps for advisor review.</p>
        </div>
      </div>
      <form ref={formRef} className="rich-report-form" aria-label="Weekly progress report" onSubmit={onSubmit}>
        <label>
          Week start
          <input name="reportWeekStart" type="date" required />
        </label>
        <label className="editor-field">
          Completed work
          <textarea name="completedWork" required placeholder="Paste images as links or describe attached evidence." />
        </label>
        <label className="editor-field">
          Blockers
          <textarea name="blockers" placeholder="Risks, dependencies, or advisor decisions needed." />
        </label>
        <label className="editor-field">
          Next steps
          <textarea name="nextSteps" required />
        </label>
        <div className="action-row">
          <button type="submit">Submit report</button>
          <KeyboardHint>Ctrl+Enter submits</KeyboardHint>
        </div>
        <FormStatus error={mutation.error?.message} success={mutation.isSuccess ? 'Weekly report submitted' : undefined} />
      </form>
    </section>
  );
}
