import { useState } from 'react';
import type { CSSProperties } from 'react';
import { useMutation, useQuery } from '@tanstack/react-query';
import { useNavigate, useParams } from 'react-router-dom';
import { Archive, BookOpenCheck, CalendarDays, CheckCircle2, ClipboardList, RotateCcw, Trash2 } from 'lucide-react';

import { Button } from '@/shared/ui/primitives/button';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/shared/ui/primitives/card';

import { useAppFeedback } from '../../shared/ui/AppFeedback';
import { DataState } from '../../shared/ui/DataState';
import { PageShell } from '../../shared/ui/PageShell';
import { StatusBadge } from '../../shared/ui/StatusBadge';
import { TaskForm } from '../tasks/TaskForm';
import { TaskStatusControl } from '../tasks/TaskStatusControl';
import { TaskTree, type TaskNode } from '../tasks/TaskTree';
import { ProjectMembersPanel } from './ProjectMembersPanel';
import { archiveProject, deleteProject, getProject, reopenProject } from './api';
import { useProjectLiveRefresh } from './useProjectLiveRefresh';

export function ProjectDashboardPage() {
  const projectId = Number(useParams().projectId ?? 0);
  const navigate = useNavigate();
  const { confirm, notify } = useAppFeedback();
  const [selectedTaskId, setSelectedTaskId] = useState<number | null>(null);
  const projectQuery = useQuery({ queryKey: ['project', projectId], queryFn: () => getProject(projectId), enabled: Boolean(projectId) });
  const liveRefresh = useProjectLiveRefresh(projectId, projectQuery.data?.latestEventId);
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
  const deleteMutation = useMutation({
    mutationFn: () => deleteProject(projectId),
    onSuccess: () => {
      notify('Project deleted', 'success');
      navigate('/projects');
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

  async function onDelete() {
    const ok = await confirm({
      title: 'Delete project?',
      message: 'This permanently deletes the project and its project-scoped tasks, materials, submissions, comments, bookings, and notifications. This action cannot be undone.',
      actionLabel: 'Delete project',
    });
    if (ok) deleteMutation.mutate();
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
  const memberNameById = new Map<number, string>();
  for (const member of project.memberships ?? []) {
    const userId = member.userId ?? member.user_id;
    if (userId) {
      memberNameById.set(userId, member.nickname || member.name || member.email || `User ${userId}`);
    }
  }
  const completed = flattenedTasks.filter((task) => task.status === 'completed').length;
  const blocked = flattenedTasks.filter((task) => task.status === 'blocked').length;
  const progress = flattenedTasks.length ? Math.round((completed / flattenedTasks.length) * 100) : 0;
  const archived = project.status === 'archived';
  const capabilities = project.capabilities ?? {
    canManageProject: false,
    canEditProject: false,
    canArchiveProject: false,
    canReopenProject: false,
    canDeleteProject: false,
    canManageMembers: false,
    canCreateTasks: false,
    canUpdateTasks: false,
    deleteDisabledReason: '',
  };
  const nextDeadline = [...flattenedTasks]
    .filter((task) => task.deadline_at)
    .sort((left, right) => new Date(left.deadline_at ?? '').getTime() - new Date(right.deadline_at ?? '').getTime())[0];

  return (
    <PageShell
      title={project.title}
      description="Dense project workspace for task planning, membership, review load, and bookings."
      actions={
        <div className="flex min-w-0 flex-col items-stretch gap-2 sm:items-end">
          <div className="flex flex-wrap items-center justify-end gap-2" aria-label="Project status">
            <StatusBadge status={project.status} />
          </div>
          <div className="flex flex-wrap items-center justify-end gap-2" aria-label="Project actions">
            {capabilities.canArchiveProject ? (
              <Button variant="destructive" type="button" onClick={onArchive} disabled={archiveMutation.isPending}>
                <Archive className="h-4 w-4" aria-hidden="true" />
                Archive project
              </Button>
            ) : null}
            {capabilities.canReopenProject ? (
              <Button variant="outline" type="button" onClick={() => reopenMutation.mutate()} disabled={reopenMutation.isPending}>
                <RotateCcw className="h-4 w-4" aria-hidden="true" />
                Reopen project
              </Button>
            ) : null}
            {capabilities.canManageProject ? (
              <Button
                variant="outline"
                type="button"
                onClick={onDelete}
                disabled={!capabilities.canDeleteProject || deleteMutation.isPending}
                title={capabilities.canDeleteProject ? undefined : capabilities.deleteDisabledReason}
              >
                <Trash2 className="h-4 w-4" aria-hidden="true" />
                Delete project
              </Button>
            ) : null}
          </div>
          {capabilities.canManageProject && !capabilities.canDeleteProject && capabilities.deleteDisabledReason ? (
            <p className="max-w-sm text-right text-xs text-muted-foreground">
              {capabilities.deleteDisabledReason}
            </p>
          ) : null}
        </div>
      }
      className="project-workspace"
    >
      {liveRefresh.state === 'stale' ? (
        <DataState state="warning" title="Project data may be stale" message="Last successful project data is still visible while live refresh retries." />
      ) : null}
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
        <MetricCard icon={BookOpenCheck} label="Pending reviews" value={pendingReviews.length} detail="weekly reports" />
        <MetricCard icon={CalendarDays} label="Upcoming bookings" value={bookings.length} detail={nextDeadline ? `Next due ${formatDate(nextDeadline.deadline_at)}` : 'reserved resources'} />
      </section>

      <div className="grid min-w-0 gap-4 overflow-hidden xl:grid-cols-[minmax(18rem,0.9fr)_minmax(22rem,1fr)_minmax(18rem,0.75fr)]">
        <section className="panel grid h-[min(34rem,calc(100vh-12rem))] min-h-[28rem] grid-rows-[auto_1fr] overflow-hidden" aria-label="Current tasks">
          <div className="mb-4 flex items-start justify-between gap-3">
            <div>
              <h2>Task plan</h2>
              <p className="text-sm text-muted-foreground">Select a task to inspect details and update status.</p>
            </div>
            <StatusBadge status={`${progress}% complete`} />
          </div>
          {tasks.length ? (
            <div className="min-h-0 overflow-y-auto pr-1">
              <TaskTree
                tasks={tasks}
                projectId={projectId}
                selectedTaskId={primaryTask?.id}
                onSelectTask={(task) => setSelectedTaskId(task.id)}
                canDeleteTasks={capabilities.canCreateTasks && !archived}
                onTaskDeleted={async () => {
                  setSelectedTaskId(null);
                  await projectQuery.refetch();
                }}
              />
            </div>
          ) : (
            <DataState state="empty" title="No tasks" message="No tasks are defined for this project." />
          )}
        </section>
        <section className="panel grid h-[min(34rem,calc(100vh-12rem))] min-h-[28rem] grid-rows-[auto_1fr] overflow-hidden" aria-label="Task details">
          <h2>Task details</h2>
          {primaryTask ? (
            <article className="mt-4 grid min-h-0 gap-3 overflow-y-auto rounded-lg border bg-muted/40 p-4">
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
                  <dd>{formatAssignees(primaryTask, memberNameById)}</dd>
                </div>
                <div>
                  <dt className="font-bold text-muted-foreground">Deadline</dt>
                  <dd>{primaryTask.deadline_at ? formatDate(primaryTask.deadline_at) : 'No deadline'}</dd>
                </div>
              </dl>
              <section className="grid gap-1 text-sm" aria-label="Selected task description">
                <h4 className="font-bold text-muted-foreground">Description</h4>
                <p className="whitespace-pre-wrap text-muted-foreground">{primaryTask.description || 'No task description provided.'}</p>
              </section>
              {capabilities.canUpdateTasks ? (
                <div className="rounded-lg border bg-background p-3">
                  <TaskStatusControl projectId={projectId} taskId={primaryTask.id} status={primaryTask.status ?? 'not_started'} disabled={archived} />
                </div>
              ) : null}
            </article>
          ) : (
            <DataState state="empty" title="No task selected" message="Select or create a task to start planning." />
          )}
        </section>
        <aside className="panel h-[min(34rem,calc(100vh-12rem))] min-h-[28rem] min-w-0 overflow-y-auto" aria-label="Members and progress">
          <h2>Members and progress</h2>
          <div className="my-4 grid place-items-center">
            <div
              className="progress-ring"
              aria-label={`Project progress ${progress}%`}
              style={{ '--progress': `${progress}%` } as CSSProperties}
            >
              <span>{progress}%</span>
            </div>
          </div>
          <ProjectMembersPanel projectId={projectId} members={project.memberships} disabled={archived} canManageMembers={capabilities.canManageMembers} />
        </aside>
      </div>

      {capabilities.canCreateTasks ? (
        <section className="panel" aria-label="Create task">
          <div className="mb-4">
            <h2>Create task</h2>
            <p className="text-sm text-muted-foreground">Add a scoped task with assignees, description, priority, and deadline.</p>
          </div>
          <TaskForm projectId={projectId} members={project.memberships} disabled={archived} />
        </section>
      ) : null}

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
            <DataState state="empty" title="No pending reviews" message="Weekly reports needing advisor action will appear here." />
          )}
        </section>
      </section>
    </PageShell>
  );
}

function flattenTasks(tasks: TaskNode[]): TaskNode[] {
  return tasks.flatMap((task) => [task, ...flattenTasks(task.children ?? [])]);
}

function formatAssignees(task: TaskNode, memberNameById: Map<number, string>) {
  const assigneeIds = task.assignee_ids?.length ? task.assignee_ids : task.assignee_id ? [task.assignee_id] : [];
  if (!assigneeIds.length) return 'Unassigned';
  return assigneeIds.map((userId) => memberNameById.get(userId) ?? `User ${userId}`).join(', ');
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
