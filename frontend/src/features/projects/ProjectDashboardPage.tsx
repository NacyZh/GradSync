import { useState } from 'react';
import { useMutation, useQuery } from '@tanstack/react-query';
import { useParams } from 'react-router-dom';
import { Archive, BookOpenCheck, CalendarDays, CheckCircle2, ClipboardList, RotateCcw } from 'lucide-react';

import { Button } from '@/shared/ui/primitives/button';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/shared/ui/primitives/card';

import { useAppFeedback } from '../../shared/ui/AppFeedback';
import { DataState } from '../../shared/ui/DataState';
import { FormStatus } from '../../shared/ui/FormStatus';
import { PageShell } from '../../shared/ui/PageShell';
import { StatusBadge } from '../../shared/ui/StatusBadge';
import { NotificationList } from '../notifications/NotificationList';
import { TaskForm } from '../tasks/TaskForm';
import { TaskStatusControl } from '../tasks/TaskStatusControl';
import { TaskTree, type TaskNode } from '../tasks/TaskTree';
import { ProjectMembersPanel } from './ProjectMembersPanel';
import { archiveProject, getProject, reopenProject } from './api';

export function ProjectDashboardPage() {
  const projectId = Number(useParams().projectId ?? 0);
  const { confirm, notify } = useAppFeedback();
  const [selectedTaskId, setSelectedTaskId] = useState<number | null>(null);
  const projectQuery = useQuery({ queryKey: ['project', projectId], queryFn: () => getProject(projectId), enabled: Boolean(projectId) });
  const archiveMutation = useMutation({
    mutationFn: () => archiveProject(projectId),
    onSuccess: () => {
      notify('Project archived', 'success');
      projectQuery.refetch();
    },
    onError: (error) => notify(error.message, 'error'),
  });
  const reopenMutation = useMutation({
    mutationFn: () => reopenProject(projectId),
    onSuccess: () => {
      notify('Project reopened', 'success');
      projectQuery.refetch();
    },
    onError: (error) => notify(error.message, 'error'),
  });

  async function onArchive() {
    const ok = await confirm({
      title: 'Archive project?',
      message: 'Archiving makes tasks, submissions, comments, bookings, and reminders read-only until reopened.',
      actionLabel: 'Archive project',
    });
    if (ok) archiveMutation.mutate();
  }

  if (projectQuery.isLoading) return <DataState state="loading" title="Loading dashboard" message="Loading project dashboard..." />;
  if (projectQuery.error) return <DataState state="error" title="Dashboard unavailable" message={projectQuery.error.message} />;
  const project = projectQuery.data;
  if (!project) return <DataState state="empty" title="No project selected" message="Select a project to continue." />;
  const tasks = (project.current_tasks ?? []) as TaskNode[];
  const flattenedTasks = flattenTasks(tasks);
  const primaryTask = flattenedTasks.find((task) => task.id === selectedTaskId) ?? flattenedTasks[0];
  const pendingReviews = project.pending_reviews ?? [];
  const bookings = project.upcoming_bookings ?? [];
  const completed = flattenedTasks.filter((task) => task.status === 'completed').length;
  const blocked = flattenedTasks.filter((task) => task.status === 'blocked').length;
  const progress = flattenedTasks.length ? Math.round((completed / flattenedTasks.length) * 100) : 0;
  const archived = project.status === 'archived';
  const nextDeadline = [...flattenedTasks]
    .filter((task) => task.deadline_at)
    .sort((left, right) => new Date(left.deadline_at ?? '').getTime() - new Date(right.deadline_at ?? '').getTime())[0];

  return (
    <PageShell
      title={project.title}
      description="Dense project workspace for task planning, membership, review load, bookings, and activity."
      actions={
        <>
          <StatusBadge status={project.status} />
          <Button variant="destructive" type="button" onClick={onArchive} disabled={archived || archiveMutation.isPending}>
            <Archive className="h-4 w-4" aria-hidden="true" />
            Archive project
          </Button>
          <Button variant="outline" type="button" onClick={() => reopenMutation.mutate()} disabled={!archived || reopenMutation.isPending}>
            <RotateCcw className="h-4 w-4" aria-hidden="true" />
            Reopen project
          </Button>
        </>
      }
      className="project-workspace"
    >
      <FormStatus error={archiveMutation.error?.message ?? reopenMutation.error?.message} success={archiveMutation.isSuccess || reopenMutation.isSuccess ? 'Project status updated' : undefined} />
      {archived ? (
        <DataState
          state="warning"
          title="Project is archived"
          message="Tasks, memberships, submissions, comments, bookings, and reminders are read-only until this project is reopened."
        />
      ) : null}

      <section className="grid gap-4 md:grid-cols-2 xl:grid-cols-4" aria-label="Project summary">
        <MetricCard icon={ClipboardList} label="Current tasks" value={flattenedTasks.length} detail={`${progress}% complete`} />
        <MetricCard icon={CheckCircle2} label="Blocked tasks" value={blocked} detail={blocked ? 'needs attention' : 'clear'} />
        <MetricCard icon={BookOpenCheck} label="Pending reviews" value={pendingReviews.length} detail="drafts and reports" />
        <MetricCard icon={CalendarDays} label="Upcoming bookings" value={bookings.length} detail={nextDeadline ? `Next due ${formatDate(nextDeadline.deadline_at)}` : 'reserved resources'} />
      </section>

      <div className="grid gap-4 xl:grid-cols-[minmax(20rem,1.1fr)_minmax(22rem,0.95fr)_minmax(18rem,0.75fr)]">
        <section className="panel" aria-label="Current tasks">
          <div className="mb-4 flex items-start justify-between gap-3">
            <div>
              <h2>Task plan</h2>
              <p className="text-sm text-muted-foreground">Hierarchy, deadlines, assignees, and status at a glance.</p>
            </div>
            <StatusBadge status={`${progress}% complete`} />
          </div>
          {tasks.length ? (
            <>
              <TaskTree tasks={tasks} projectId={projectId} selectedTaskId={primaryTask?.id} onSelectTask={(task) => setSelectedTaskId(task.id)} />
              {primaryTask ? (
                <div className="mt-4 rounded-lg border bg-muted/40 p-3">
                  <TaskStatusControl projectId={projectId} taskId={primaryTask.id} status={primaryTask.status ?? 'not_started'} disabled={archived} />
                </div>
              ) : null}
            </>
          ) : (
            <DataState state="empty" title="No tasks" message="No tasks are defined for this project." />
          )}
        </section>
        <section className="panel" aria-label="Task details">
          <h2>Task details</h2>
          {primaryTask ? (
            <article className="mb-5 grid gap-3 rounded-lg border bg-muted/40 p-4">
              <div className="flex flex-wrap items-center justify-between gap-2">
                <h3 className="text-lg font-extrabold">{primaryTask.title}</h3>
                <StatusBadge status={primaryTask.status ?? 'not_started'} />
              </div>
              <dl className="grid gap-2 text-sm sm:grid-cols-2">
                <div>
                  <dt className="font-bold text-muted-foreground">Priority</dt>
                  <dd>Priority: {primaryTask.priority ?? 'normal'}</dd>
                </div>
                <div>
                  <dt className="font-bold text-muted-foreground">Assignee</dt>
                  <dd>{primaryTask.assignee_id ? `User ${primaryTask.assignee_id}` : 'Unassigned'}</dd>
                </div>
                <div>
                  <dt className="font-bold text-muted-foreground">Deadline</dt>
                  <dd>{primaryTask.deadline_at ? formatDate(primaryTask.deadline_at) : 'No deadline'}</dd>
                </div>
              </dl>
              <p className="text-sm text-muted-foreground">
                Use the task plan status control to update this task while keeping the hierarchy visible.
              </p>
            </article>
          ) : (
            <DataState state="empty" title="No task selected" message="Select or create a task to start planning." />
          )}
          <TaskForm projectId={projectId} disabled={archived} />
        </section>
        <aside className="panel" aria-label="Members and progress">
          <h2>Members and progress</h2>
          <div className="my-4 grid place-items-center">
            <div className="progress-ring" aria-label={`Project progress ${progress}%`}>
              <span>{progress}%</span>
            </div>
          </div>
          <ProjectMembersPanel projectId={projectId} members={project.memberships} disabled={archived} />
        </aside>
      </div>

      <section className="dashboard-grid">
        <section className="panel" aria-label="Pending reviews">
          <h2>Pending reviews</h2>
          {pendingReviews.length ? (
            <ul className="timeline">
              {pendingReviews.map((review, index) => (
                <li key={index}>Review {String((review as { target_type?: string }).target_type ?? 'submission')} #{String((review as { target_id?: string }).target_id ?? index + 1)}</li>
              ))}
            </ul>
          ) : (
            <DataState state="empty" title="No pending reviews" message="Drafts and reports needing advisor action will appear here." />
          )}
        </section>
        <section className="panel" aria-label="Activity">
          <h2>Recent activity</h2>
          {project.activity?.length ? (
            <ul className="timeline">
              {project.activity.map((event, index) => (
                <li key={`${event.event_type}-${index}`}>
                  <strong>{event.event_type.replaceAll('_', ' ')}</strong>
                  <span>{event.summary}</span>
                </li>
              ))}
            </ul>
          ) : (
            <DataState state="empty" title="No activity yet" message="Task, submission, comment, booking, and notification events will appear here." />
          )}
        </section>
      </section>
      <NotificationList projectId={projectId} />
    </PageShell>
  );
}

function flattenTasks(tasks: TaskNode[]): TaskNode[] {
  return tasks.flatMap((task) => [task, ...flattenTasks(task.children ?? [])]);
}

function formatDate(value?: string) {
  if (!value) return 'No date';
  return new Intl.DateTimeFormat(undefined, { month: 'short', day: 'numeric', year: 'numeric' }).format(new Date(value));
}

function MetricCard({ icon: Icon, label, value, detail }: { icon: typeof ClipboardList; label: string; value: number; detail: string }) {
  return (
    <Card>
      <CardHeader className="flex-row items-start justify-between gap-3 space-y-0">
        <div>
          <CardDescription>{label}</CardDescription>
          <CardTitle className="mt-2 text-3xl">{value}</CardTitle>
        </div>
        <span className="rounded-md bg-muted p-2 text-primary">
          <Icon className="h-5 w-5" aria-hidden="true" />
        </span>
      </CardHeader>
      <CardContent className="text-sm text-muted-foreground">{detail}</CardContent>
    </Card>
  );
}
