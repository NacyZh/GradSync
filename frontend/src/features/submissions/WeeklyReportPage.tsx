import { useMutation } from '@tanstack/react-query';
import { useParams } from 'react-router-dom';

import { FormStatus } from '../../shared/ui/FormStatus';
import { submitWeeklyReport } from './api';

export function WeeklyReportPage() {
  const projectId = Number(useParams().projectId ?? 0);
  const mutation = useMutation({ mutationFn: submitWeeklyReport.bind(null, projectId) });

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

  return (
    <section>
      <h1>Weekly progress report</h1>
      <form aria-label="Weekly progress report" onSubmit={onSubmit}>
        <label>
          Week start
          <input name="reportWeekStart" type="date" required />
        </label>
        <label>
          Completed work
          <textarea name="completedWork" required />
        </label>
        <label>
          Blockers
          <textarea name="blockers" />
        </label>
        <label>
          Next steps
          <textarea name="nextSteps" required />
        </label>
        <button type="submit">Submit report</button>
        <FormStatus error={mutation.error?.message} success={mutation.isSuccess ? 'Weekly report submitted' : undefined} />
      </form>
    </section>
  );
}
