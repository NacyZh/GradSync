import { useQuery, useQueryClient } from '@tanstack/react-query';
import { useEffect, useMemo, useState } from 'react';
import { Link, useSearchParams } from 'react-router-dom';

import { useAuth } from '../features/auth/AuthProvider';
import { listProjects } from '../features/projects/api';
import { CalendarAgenda } from '../features/schedules/CalendarAgenda';
import { CalendarGrid } from '../features/schedules/CalendarGrid';
import { CalendarToolbar } from '../features/schedules/CalendarToolbar';
import { ScheduleDetailPanel } from '../features/schedules/ScheduleDetailPanel';
import { ScheduleFormDialog } from '../features/schedules/ScheduleFormDialog';
import {
  calendarErrorMessage,
  calendarQueryKey,
  listCalendarOccurrences,
  completeSchedule,
  cancelSchedule,
  createSchedule,
  deleteSchedule,
  periodForView,
  publishSchedule,
  retrieveSchedule,
  updateSchedule,
  type CalendarOccurrence,
  type CalendarSource,
  type CalendarView,
  type ScheduleChangeScope,
  type ScheduleDetail,
  type ScheduleWrite,
} from '../features/schedules/api';
import { useCalendarLiveRefresh } from '../features/schedules/useCalendarLiveRefresh';
import type { ApiError } from '../shared/api/client';
import { useAppFeedback } from '../shared/ui/AppFeedback';
import { AsyncState } from '../shared/ui/AsyncState';

export function HomePage() {
  const queryClient = useQueryClient();
  const { notify } = useAppFeedback();
  const { user, isLoading: isLoadingUser } = useAuth();
  const [searchParams] = useSearchParams();
  const [calendarView, setCalendarView] = useState<CalendarView>('month');
  const [calendarAnchor, setCalendarAnchor] = useState(() => {
    const requestedDate = searchParams.get('date');
    const parsed = requestedDate ? new Date(`${requestedDate}T12:00:00`) : new Date();
    return Number.isNaN(parsed.getTime()) ? new Date() : parsed;
  });
  const [calendarSources, setCalendarSources] = useState<CalendarSource[]>([
    'schedule', 'project', 'task', 'report', 'booking',
  ]);
  const [selectedOccurrence, setSelectedOccurrence] = useState<CalendarOccurrence | null>(null);
  const [scheduleFormOpen, setScheduleFormOpen] = useState(false);
  const [editingSchedule, setEditingSchedule] = useState<ScheduleDetail | null>(null);
  const [editScope, setEditScope] = useState<ScheduleChangeScope>('series');
  const [editOccurrenceKey, setEditOccurrenceKey] = useState<string | null>(null);
  const calendarPeriod = useMemo(
    () => periodForView(calendarAnchor, calendarView),
    [calendarAnchor, calendarView],
  );
  const projectsQuery = useQuery({
    queryKey: ['projects'],
    queryFn: listProjects,
    enabled: Boolean(user),
  });

  const projects = projectsQuery.data?.results ?? [];
  const calendarQuery = useQuery({
    queryKey: calendarQueryKey(calendarPeriod, calendarSources),
    queryFn: () => listCalendarOccurrences(calendarPeriod, calendarSources),
    enabled: Boolean(user),
    placeholderData: (previous) => previous,
  });
  const liveRefresh = useCalendarLiveRefresh(Boolean(user));
  const occurrences = (calendarQuery.data?.results ?? []).filter(
    (item): item is CalendarOccurrence => Boolean(item?.occurrenceId),
  );
  useEffect(() => {
    const requestedItem = searchParams.get('item');
    if (!requestedItem || selectedOccurrence?.occurrenceId === requestedItem) return;
    const match = occurrences.find((item) => item.occurrenceId === requestedItem);
    if (match) setSelectedOccurrence(match);
  }, [occurrences, searchParams, selectedOccurrence?.occurrenceId]);
  const role = user?.global_role;
  const latestProject = projects[0];
  const heading =
    role === 'student' ? 'Student workspace' : role === 'advisor' ? 'Advisor workspace' : role === 'admin' ? 'Operations workspace' : 'GradSync dashboard';
  const description =
    role === 'student'
      ? 'Open assigned projects and continue submission work.'
      : role === 'admin'
        ? 'Oversee project health, account operations, approvals, and shared research resources.'
        : 'Review project work and keep active research moving.';

  async function refreshCalendar() {
    await queryClient.invalidateQueries({ queryKey: ['calendar'] });
  }

  async function submitSchedule(payload: ScheduleWrite) {
    try {
      if (editingSchedule) {
        if (editingSchedule.scope === 'personal' && payload.scope === 'group' && payload.audience) {
          await publishSchedule(editingSchedule.id, editingSchedule.version, payload.audience, payload.reminders);
          notify('Schedule published', 'success');
        } else {
          const fields: Partial<ScheduleWrite> = { ...payload };
          delete fields.scope;
          delete fields.audience;
          delete fields.confirmConflicts;
          await updateSchedule(editingSchedule.id, {
            expectedVersion: editingSchedule.version,
            changeScope: editScope,
            occurrenceKey: editScope === 'series' ? null : editOccurrenceKey,
            fields,
            confirmConflicts: payload.confirmConflicts,
          });
          notify('Schedule updated', 'success');
        }
      } else {
        await createSchedule(payload);
        notify(payload.scope === 'group' ? 'Schedule published' : 'Schedule created', 'success');
      }
      setScheduleFormOpen(false);
      setEditingSchedule(null);
      await refreshCalendar();
    } catch (error) {
      const apiError = error as ApiError;
      if (apiError.code !== 'schedule_conflict_confirmation_required') {
        notify(apiError.message || 'Unable to save schedule.', 'error');
      }
      throw error;
    }
  }

  async function beginEdit(occurrence: CalendarOccurrence, scope: ScheduleChangeScope, occurrenceKey: string) {
    if (!occurrence.scheduleId) return;
    try {
      const detail = await retrieveSchedule(occurrence.scheduleId);
      setEditingSchedule(detail);
      setEditScope(scope);
      setEditOccurrenceKey(occurrenceKey);
      setScheduleFormOpen(true);
    } catch (error) {
      notify((error as ApiError).message || 'Unable to open schedule.', 'error');
    }
  }

  async function completeSelected(occurrence: CalendarOccurrence, scope: ScheduleChangeScope, occurrenceKey: string) {
    if (!occurrence.scheduleId || !occurrence.version) return;
    try {
      await completeSchedule(occurrence.scheduleId, occurrence.version, scope, scope === 'series' ? null : occurrenceKey);
      notify('Schedule completed', 'success');
      setSelectedOccurrence(null);
      await refreshCalendar();
    } catch (error) {
      notify((error as ApiError).message || 'Unable to complete schedule.', 'error');
    }
  }

  async function deleteSelected(occurrence: CalendarOccurrence, scope: ScheduleChangeScope, occurrenceKey: string) {
    if (!occurrence.scheduleId || !occurrence.version) return;
    try {
      await deleteSchedule(occurrence.scheduleId, occurrence.version, scope, scope === 'series' ? null : occurrenceKey);
      notify('Schedule deleted', 'success');
      setSelectedOccurrence(null);
      await refreshCalendar();
    } catch (error) {
      notify((error as ApiError).message || 'Unable to delete schedule.', 'error');
    }
  }

  async function cancelSelected(occurrence: CalendarOccurrence, scope: ScheduleChangeScope, occurrenceKey: string) {
    if (!occurrence.scheduleId || !occurrence.version) return;
    try {
      await cancelSchedule(occurrence.scheduleId, occurrence.version, scope, scope === 'series' ? null : occurrenceKey);
      notify('Schedule cancelled', 'success');
      setSelectedOccurrence(null);
      await refreshCalendar();
    } catch (error) {
      notify((error as ApiError).message || 'Unable to cancel schedule.', 'error');
    }
  }

  return (
    <>
      <section className="page-heading dashboard-hero">
        <div>
          <h1>{heading}</h1>
          <p>{description}</p>
        </div>
      </section>

      {isLoadingUser ? <AsyncState state="loading" message="Loading account" /> : null}

      {user && (
        <section className="calendar-workspace" aria-label="Dashboard calendar">
          <CalendarToolbar
            anchor={calendarAnchor}
            view={calendarView}
            sources={calendarSources}
            onAnchorChange={setCalendarAnchor}
            onViewChange={setCalendarView}
            onSourcesChange={setCalendarSources}
            onCreate={() => { setEditingSchedule(null); setScheduleFormOpen(true); }}
          />
          {calendarQuery.isLoading ? <AsyncState state="loading" message="Loading calendar" /> : null}
          {calendarQuery.error && occurrences.length === 0 ? (
            <AsyncState
              state="error"
              message={calendarErrorMessage(calendarQuery.error)}
              action={<button type="button" className="inline-action" onClick={() => calendarQuery.refetch()}>Retry</button>}
            />
          ) : null}
          <div className="calendar-workspace-body" aria-busy={calendarQuery.isFetching}>
            <div className="calendar-primary-region">
              {calendarView === 'agenda' ? (
                <CalendarAgenda occurrences={occurrences} selectedId={selectedOccurrence?.occurrenceId ?? null} onSelect={setSelectedOccurrence} />
              ) : (
                <CalendarGrid anchor={calendarAnchor} view={calendarView} occurrences={occurrences} selectedId={selectedOccurrence?.occurrenceId ?? null} onSelect={setSelectedOccurrence} />
              )}
              {!calendarQuery.isLoading && occurrences.length === 0 ? (
                <p className="calendar-empty" role="status">No schedule items in this period.</p>
              ) : null}
            </div>
            <ScheduleDetailPanel
              occurrence={selectedOccurrence}
              upcoming={occurrences}
              onSelect={setSelectedOccurrence}
              onClose={() => setSelectedOccurrence(null)}
              onEdit={(scope, key) => { if (selectedOccurrence) void beginEdit(selectedOccurrence, scope, key); }}
              onComplete={(scope, key) => { if (selectedOccurrence) void completeSelected(selectedOccurrence, scope, key); }}
              onDelete={(scope, key) => { if (selectedOccurrence) void deleteSelected(selectedOccurrence, scope, key); }}
              onCancel={(scope, key) => { if (selectedOccurrence) void cancelSelected(selectedOccurrence, scope, key); }}
            />
          </div>
          {calendarQuery.isFetching && calendarQuery.data ? <p className="calendar-updating" role="status">Updating calendar</p> : null}
          {liveRefresh.isStale ? <p className="calendar-updating" role="status">Live updates paused. <button type="button" className="inline-action" onClick={() => void liveRefresh.retry()}>Retry</button></p> : null}
        </section>
      )}

      {user ? (
        <ScheduleFormDialog
          open={scheduleFormOpen}
          onOpenChange={(open) => { setScheduleFormOpen(open); if (!open) setEditingSchedule(null); }}
          role={user.global_role}
          initial={editingSchedule}
          onSubmit={submitSchedule}
        />
      ) : null}

      {user && (
        <section className="grid gap-4 xl:grid-cols-[minmax(24rem,1.25fr)_minmax(18rem,0.75fr)]" aria-label="Dashboard work overview">
          <article className="panel">
            <div className="mb-4 flex flex-wrap items-start justify-between gap-3">
              <div>
                <h2>Your projects</h2>
                <p className="text-sm text-muted-foreground">{projects.length} visible workspaces</p>
              </div>
              {(role === 'admin' || role === 'advisor') ? (
                <Link className="inline-action font-bold text-primary" to="/projects/new">New project</Link>
              ) : null}
            </div>
            {projectsQuery.isLoading ? <AsyncState state="loading" message="Loading projects" /> : null}
            {projectsQuery.error ? (
              <AsyncState state="error" message={projectsQuery.error.message} />
            ) : null}
            {!projectsQuery.isLoading && !projectsQuery.error && projects.length === 0 ? (
              <AsyncState state="empty" message="No visible projects yet" />
            ) : null}
            {projects.length > 0 ? (
              <ul className="project-list">
                {projects.map((project) => (
                  <li key={project.id}>
                    <Link to={`/projects/${project.id}`}>
                      <span>{project.title}</span>
                      <small>{project.status}</small>
                    </Link>
                  </li>
                ))}
              </ul>
            ) : null}
          </article>
          {role === 'student' ? (
            <article className="panel">
              <h2>Student work queue</h2>
              <div className="workflow-list">
                {latestProject ? <Link to={`/projects/${latestProject.id}/reports`}>Weekly reports</Link> : null}
                <Link to="/resources">Book a resource</Link>
              </div>
            </article>
          ) : role === 'admin' ? (
            <article className="panel">
              <h2>Operations queue</h2>
              <div className="workflow-list">
                <Link to="/projects/new">New project</Link>
                <Link to="/admin/accounts">Account operations</Link>
                <Link to="/admin/role-activations">Role approvals</Link>
                <Link to="/resources">Resource operations</Link>
                {latestProject ? <Link to={`/projects/${latestProject.id}`}>Project health dashboard</Link> : null}
                {latestProject ? <Link to={`/projects/${latestProject.id}/reviews`}>Review queue</Link> : null}
                {latestProject ? <Link to={`/projects/${latestProject.id}/reports`}>Report oversight</Link> : null}
              </div>
            </article>
          ) : (
            <article className="panel">
              <h2>Advisor work queue</h2>
              <div className="workflow-list">
                <Link to="/resources">Reserve lab equipment or seats</Link>
                {latestProject ? <Link to={`/projects/${latestProject.id}/reviews`}>Open review queue</Link> : null}
                {latestProject ? <Link to={`/projects/${latestProject.id}`}>Open project dashboard</Link> : null}
              </div>
            </article>
          )}
        </section>
      )}
    </>
  );
}
