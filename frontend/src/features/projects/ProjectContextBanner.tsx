import { useQuery } from '@tanstack/react-query';
import { useParams } from 'react-router-dom';

import { getProject } from './api';
import { ProjectContextBar } from '../../shared/ui/ProjectContextBar';

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
    <ProjectContextBar
      projectId={projectId}
      title={project?.title}
      status={project?.status}
      isLoading={projectQuery.isLoading}
    />
  );
}
