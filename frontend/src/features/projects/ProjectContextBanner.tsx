import { useQuery } from '@tanstack/react-query';
import { useParams } from 'react-router-dom';

import { useAuth } from '../auth/AuthProvider';
import { getProject } from './api';
import { ProjectContextBar } from '../../shared/ui/ProjectContextBar';
import { AlertTriangle } from 'lucide-react';
import { useI18n } from '@/shared/i18n/I18nProvider';

export function ProjectContextBanner() {
  const projectId = Number(useParams().projectId ?? 0);
  const { user } = useAuth();
  const { t } = useI18n();
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
    <div className="grid gap-2">
      <ProjectContextBar
        projectId={projectId}
        title={project?.title}
        status={project?.status}
        userRole={user?.global_role}
        isLoading={projectQuery.isLoading}
      />
      {project?.governanceState === 'hold' ? (
        <div className="flex items-start gap-2 border-b border-amber-300 bg-amber-50 px-4 py-2 text-sm text-amber-950" role="status">
          <AlertTriangle className="mt-0.5 h-4 w-4 flex-none" aria-hidden="true" />
          <span>{t('projectGovernanceHoldPrefix')} {project.governanceHoldReason || t('administratorReviewRequired')}.</span>
        </div>
      ) : null}
    </div>
  );
}
