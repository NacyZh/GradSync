import { useMutation, useQuery } from '@tanstack/react-query';
import { useParams } from 'react-router-dom';

import { useAppFeedback } from '../../shared/ui/AppFeedback';
import { AsyncState } from '../../shared/ui/AsyncState';
import { FormStatus } from '../../shared/ui/FormStatus';
import { NotificationList } from '../notifications/NotificationList';
import { TaskForm } from '../tasks/TaskForm';
import { TaskStatusControl } from '../tasks/TaskStatusControl';
import { TaskTree, type TaskNode } from '../tasks/TaskTree';
import { ProjectMembersPanel } from './ProjectMembersPanel';
import { archiveProject, getProject, reopenProject } from './api';

export function ProjectDashboardPage() {
  const projectId = Number(useParams().projectId ?? 0);
  const { confirm, notify } = useAppFeedback();
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

  if (projectQuery.isLoading) return <AsyncState state="loading" message="Loading project dashboard..." />;
  if (projectQuery.error) return <AsyncState state="error" message={projectQuery.error.message} />;
  const project = projectQuery.data;
  if (!project) return <AsyncState state="empty" message="Select a project to continue." />;
  const tasks = (project.current_tasks ?? []) as TaskNode[];
  const primaryTask = tasks.find((task) => !tasks.some((candidate) => candidate.children?.some((child) => child.id === task.id))) ?? tasks[0];
  const pendingReviews = project.pending_reviews ?? [];
  const bookings = project.upcoming_bookings ?? [];
  const completed = tasks.filter((task) => task.status === 'completed').length;
  const progress = tasks.length ? Math.round((completed / tasks.length) * 100) : 0;

  return (
    <section className="project-workspace">
      <div className="page-heading">
        <div>
          <h1>{project.title}</h1>
          <p>Project status: <span className={`status-pill ${project.status}`}>{project.status}</span></p>
        </div>
        <div className="action-row">
          <button className="button danger" type="button" onClick={onArchive} disabled={project.status === 'archived'}>
            Archive project
          </button>
          <button className="button" type="button" onClick={() => reopenMutation.mutate()} disabled={project.status === 'active'}>
            Reopen project
          </button>
        </div>
      </div>
      <FormStatus error={archiveMutation.error?.message ?? reopenMutation.error?.message} success={archiveMutation.isSuccess || reopenMutation.isSuccess ? 'Project status updated' : undefined} />

      <section className="dashboard-grid" aria-label="Project summary">
        <article className="metric-card">
          <span>Current tasks</span>
          <strong>{tasks.length}</strong>
          <small>{progress}% complete</small>
        </article>
        <article className="metric-card">
          <span>Pending reviews</span>
          <strong>{pendingReviews.length}</strong>
          <small>drafts and reports</small>
        </article>
        <article className="metric-card">
          <span>Upcoming bookings</span>
          <strong>{bookings.length}</strong>
          <small>reserved resources</small>
        </article>
      </section>

      <div className="three-column-workspace">
        <section className="panel" aria-label="Current tasks">
          <h2>Task plan</h2>
          {tasks.length ? <TaskTree tasks={tasks} projectId={projectId} /> : <AsyncState state="empty" message="No tasks are defined for this project." />}
          {primaryTask ? <TaskStatusControl projectId={projectId} taskId={primaryTask.id} status={primaryTask.status ?? 'not_started'} /> : null}
        </section>
        <section className="panel" aria-label="Task details">
          <h2>Task details</h2>
          {primaryTask ? (
            <article>
              <h3>{primaryTask.title}</h3>
              <p>Status: {primaryTask.status ?? 'not_started'}</p>
              <p>Priority: {primaryTask.priority ?? 'normal'}</p>
            </article>
          ) : (
            <AsyncState state="empty" message="Select or create a task to start planning." />
          )}
          <TaskForm projectId={projectId} />
        </section>
        <aside className="panel" aria-label="Members and progress">
          <h2>Members and progress</h2>
          <div className="progress-ring" aria-label={`Project progress ${progress}%`}>
            <span>{progress}%</span>
          </div>
          <ProjectMembersPanel projectId={projectId} members={project.memberships} />
        </aside>
      </div>

      <section className="dashboard-grid">
        <section className="panel" aria-label="Pending reviews">
          <h2>Pending reviews</h2>
          <ul className="timeline">
            {pendingReviews.map((review, index) => (
              <li key={index}>Review {String((review as { target_type?: string }).target_type ?? 'submission')} #{String((review as { target_id?: string }).target_id ?? index + 1)}</li>
            ))}
          </ul>
        </section>
        <section className="panel" aria-label="Activity">
          <h2>Recent activity</h2>
          <ul className="timeline">
            {project.activity?.map((event, index) => (
              <li key={`${event.event_type}-${index}`}>
                <strong>{event.event_type.replaceAll('_', ' ')}</strong>
                <span>{event.summary}</span>
              </li>
            ))}
          </ul>
        </section>
      </section>
      <NotificationList projectId={projectId} />
    </section>
  );
}
