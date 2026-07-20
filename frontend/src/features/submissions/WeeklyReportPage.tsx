import { useMutation, useQuery } from '@tanstack/react-query';
import { useParams } from 'react-router-dom';
import { useCallback, useRef } from 'react';
import { ClipboardCheck } from 'lucide-react';

import { Button } from '@/shared/ui/primitives/button';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/shared/ui/primitives/card';
import { KeyboardHint, useAppFeedback, useSubmitShortcut } from '../../shared/ui/AppFeedback';
import { DataState } from '../../shared/ui/DataState';
import { FieldGroup, FormField, TextareaField } from '../../shared/ui/FormField';
import { PageShell } from '../../shared/ui/PageShell';
import { useAuth } from '../auth/AuthProvider';
import { WeeklyReportHistory } from './WeeklyReportHistory';
import {
  deleteProjectReportSchedule,
  getProjectReportSchedule,
  listReports,
  saveProjectReportSchedule,
  submitWeeklyReport,
} from './api';

export function WeeklyReportPage() {
  const projectId = Number(useParams().projectId ?? 0);
  const { user } = useAuth();
  const formRef = useRef<HTMLFormElement>(null);
  const { notify, confirm } = useAppFeedback();
  const canSubmitReports = user?.global_role === 'student';
  const canManageSchedule = user?.global_role === 'advisor' || user?.global_role === 'admin';
  const reportsQuery = useQuery({
    queryKey: ['reports', projectId],
    queryFn: () => listReports(projectId),
    enabled: Boolean(projectId),
  });
  const mutation = useMutation({
    mutationFn: submitWeeklyReport.bind(null, projectId),
    onSuccess: () => {
      notify('Weekly report submitted', 'success');
      reportsQuery.refetch();
    },
    onError: (error) => notify(error.message, 'error'),
  });
  const reportScheduleQuery = useQuery({
    queryKey: ['projectReportSchedule', projectId],
    queryFn: () => getProjectReportSchedule(projectId),
    enabled: Boolean(projectId && user),
  });
  const scheduleMutation = useMutation({
    mutationFn: (payload: { weekday: number; deadlineLocalTime: string; timezone: string; expectedVersion?: number }) =>
      saveProjectReportSchedule(projectId, payload),
    onSuccess: (policy) => {
      reportScheduleQuery.refetch();
      notify(`Weekly report deadline saved for ${weekdayLabel(policy.weekday)}`, 'success');
    },
    onError: (error) => notify(error.message, 'error'),
  });
  const removeScheduleMutation = useMutation({
    mutationFn: (version: number) => deleteProjectReportSchedule(projectId, version),
    onSuccess: () => {
      reportScheduleQuery.refetch();
      notify('Weekly report deadline removed', 'success');
    },
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

  function onScheduleSubmit(event: React.FormEvent<HTMLFormElement>) {
    event.preventDefault();
    const form = new FormData(event.currentTarget);
    scheduleMutation.mutate({
      weekday: Number(form.get('weekday')),
      deadlineLocalTime: String(form.get('deadlineLocalTime')),
      timezone: String(form.get('timezone')),
      expectedVersion: reportScheduleQuery.data?.version,
    });
  }

  async function removeSchedule() {
    const policy = reportScheduleQuery.data;
    if (!policy) return;
    const accepted = await confirm({
      title: 'Remove weekly report deadline?',
      message: 'Future report deadlines will disappear from member calendars. Submitted reports are unchanged.',
      actionLabel: 'Remove schedule',
    });
    if (accepted) removeScheduleMutation.mutate(policy.version);
  }

  const submitShortcut = useCallback(() => {
    formRef.current?.requestSubmit();
  }, []);
  useSubmitShortcut(submitShortcut);

  return (
    <PageShell
      title="Weekly progress report"
      description="Submit weekly progress updates, track review decisions, and resubmit revisions when a report is returned."
      className="submission-workspace"
    >
      <Card className="mb-4" aria-label="Weekly report schedule">
        <CardHeader>
          <CardTitle>Weekly report deadline</CardTitle>
          <CardDescription>Project-owned schedule used for future member calendar deadlines.</CardDescription>
        </CardHeader>
        <CardContent>
          {reportScheduleQuery.isLoading ? <DataState state="loading" message="Loading report deadline" /> : null}
          {reportScheduleQuery.error ? <DataState state="error" message={reportScheduleQuery.error.message} /> : null}
          {!reportScheduleQuery.isLoading && !reportScheduleQuery.error && canManageSchedule ? (
            <form className="grid gap-3 md:grid-cols-[1fr_1fr_1.4fr_auto] md:items-end" onSubmit={onScheduleSubmit}>
              <label className="grid gap-1.5 text-sm font-bold">
                Weekday
                <select name="weekday" className="min-h-10 rounded-md border bg-background px-3" defaultValue={reportScheduleQuery.data?.weekday ?? 5}>
                  {[1, 2, 3, 4, 5, 6, 7].map((day) => <option key={day} value={day}>{weekdayLabel(day)}</option>)}
                </select>
              </label>
              <FormField id="report-deadline-time" name="deadlineLocalTime" label="Deadline time" type="time" required defaultValue={reportScheduleQuery.data?.deadlineLocalTime ?? '18:00'} />
              <FormField id="report-deadline-timezone" name="timezone" label="Timezone" required defaultValue={reportScheduleQuery.data?.timezone ?? Intl.DateTimeFormat().resolvedOptions().timeZone} />
              <div className="flex flex-wrap gap-2">
                <Button type="submit" disabled={scheduleMutation.isPending}>Save</Button>
                {reportScheduleQuery.data ? <Button type="button" variant="outline" disabled={removeScheduleMutation.isPending} onClick={removeSchedule}>Remove</Button> : null}
              </div>
            </form>
          ) : null}
          {!reportScheduleQuery.isLoading && !reportScheduleQuery.error && !canManageSchedule ? (
            reportScheduleQuery.data ? (
              <p className="text-sm"><strong>{weekdayLabel(reportScheduleQuery.data.weekday)}</strong> at {reportScheduleQuery.data.deadlineLocalTime} ({reportScheduleQuery.data.timezone})</p>
            ) : <DataState state="empty" message="No weekly report deadline is configured." />
          ) : null}
        </CardContent>
      </Card>
      <div className="grid gap-4 xl:grid-cols-[minmax(24rem,1.2fr)_minmax(18rem,0.8fr)]">
        {canSubmitReports ? (
          <Card>
            <CardHeader>
              <CardTitle className="flex items-center gap-2">
                <ClipboardCheck className="h-4 w-4" aria-hidden="true" />
                Report editor
              </CardTitle>
              <CardDescription>Submit one project-scoped weekly update. Returned weeks can be resubmitted as a new revision.</CardDescription>
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
              </form>
            </CardContent>
          </Card>
        ) : (
          <Card aria-label="Report oversight">
            <CardHeader>
              <CardTitle>Report oversight</CardTitle>
              <CardDescription>Administrators and advisors monitor submitted progress reports without creating student updates.</CardDescription>
            </CardHeader>
            <CardContent>
              {reportsQuery.isLoading ? <DataState state="loading" message="Loading reports" /> : null}
              {reportsQuery.error ? <DataState state="error" message={reportsQuery.error.message} /> : null}
              {!reportsQuery.isLoading && !reportsQuery.error ? <DataState state="success" message="Use report history to follow weekly project progress and returned revisions." /> : null}
            </CardContent>
          </Card>
        )}
        <WeeklyReportHistory reports={reportsQuery.data?.results ?? (mutation.data ? [mutation.data] : [])} />
      </div>
    </PageShell>
  );
}

function weekdayLabel(day: number) {
  return ['Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Saturday', 'Sunday'][day - 1] ?? 'Unknown day';
}
