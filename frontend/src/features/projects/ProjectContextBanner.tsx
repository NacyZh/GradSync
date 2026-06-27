import { useQuery } from '@tanstack/react-query';
import { Link, useParams } from 'react-router-dom';

import { getProject } from './api';

export function ProjectContextBanner() {
  const projectId = Number(useParams().projectId ?? 0);
  const projectQuery = useQuery({
    queryKey: ['project-context', projectId],
    queryFn: () => getProject(projectId),
    enabled: Boolean(projectId),
  });

  if (!projectId) {
    return null;
  }

  const project = projectQuery.data;

  return (
    <section aria-label="Selected project context">
      <span>Selected project</span>
      <strong>{project?.title ?? `Project ${projectId}`}</strong>
      {project?.status ? <span>{project.status}</span> : null}
      <nav aria-label="Project workflow">
        <Link to={`/projects/${projectId}`}>Dashboard</Link>
        <Link to={`/projects/${projectId}/drafts`}>Drafts</Link>
        <Link to={`/projects/${projectId}/reports`}>Reports</Link>
        <Link to={`/projects/${projectId}/reviews`}>Reviews</Link>
        <Link to={`/projects/${projectId}/resources`}>Resources</Link>
      </nav>
    </section>
  );
}
