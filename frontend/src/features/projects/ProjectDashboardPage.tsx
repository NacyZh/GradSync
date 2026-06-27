import { useMutation, useQuery } from '@tanstack/react-query';
import { useParams } from 'react-router-dom';

import { AsyncState } from '../../shared/ui/AsyncState';
import { FormStatus } from '../../shared/ui/FormStatus';
import { NotificationList } from '../notifications/NotificationList';
import { ProjectMembersPanel } from './ProjectMembersPanel';
import { archiveProject, getProject, reopenProject } from './api';

export function ProjectDashboardPage() {
  const projectId = Number(useParams().projectId ?? 0);
  const projectQuery = useQuery({ queryKey: ['project', projectId], queryFn: () => getProject(projectId), enabled: Boolean(projectId) });
  const archiveMutation = useMutation({
    mutationFn: () => archiveProject(projectId),
    onSuccess: () => projectQuery.refetch(),
  });
  const reopenMutation = useMutation({
    mutationFn: () => reopenProject(projectId),
    onSuccess: () => projectQuery.refetch(),
  });

  if (projectQuery.isLoading) return <AsyncState state="loading" message="Loading project dashboard..." />;
  if (projectQuery.error) return <AsyncState state="error" message={projectQuery.error.message} />;
  const project = projectQuery.data;
  if (!project) return <AsyncState state="empty" message="Select a project to continue." />;

  return (
    <section>
      <h1>{project.title}</h1>
      <p>Project status: {project.status}</p>
      <button type="button" onClick={() => archiveMutation.mutate()} disabled={project.status === 'archived'}>
        Archive project
      </button>
      <button type="button" onClick={() => reopenMutation.mutate()} disabled={project.status === 'active'}>
        Reopen project
      </button>
      <FormStatus error={archiveMutation.error?.message ?? reopenMutation.error?.message} success={archiveMutation.isSuccess || reopenMutation.isSuccess ? 'Project status updated' : undefined} />
      <ProjectMembersPanel projectId={projectId} members={project.memberships} />
      <section aria-label="Current tasks">
        <h2>Current tasks</h2>
        <p>{project.current_tasks?.length ?? 0} active tasks</p>
      </section>
      <section aria-label="Pending reviews">
        <h2>Pending reviews</h2>
        <p>{project.pending_reviews?.length ?? 0} pending reviews</p>
      </section>
      <section aria-label="Upcoming bookings">
        <h2>Upcoming bookings</h2>
        <p>{project.upcoming_bookings?.length ?? 0} upcoming bookings</p>
      </section>
      <section aria-label="Activity">
        <h2>Activity</h2>
        <ul>
          {project.activity?.map((event, index) => <li key={`${event.event_type}-${index}`}>{event.summary}</li>)}
        </ul>
      </section>
      <NotificationList projectId={projectId} />
    </section>
  );
}
